from collections import defaultdict
from datetime import date

from flask import Blueprint, redirect, url_for
from flask_inertia import render_inertia

from src.database import SessionLocal, TrackingEntry
from src.services.rule37 import compute_37_best

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def list_entries():
    with SessionLocal() as db:
        today = date.today()
        entries_data = []
        for e in db.query(TrackingEntry).order_by(TrackingEntry.flight_date).all():
            valid = [
                s for s in e.price_snapshots if s.scrape_status == "success" and s.fare
            ]
            fares = [float(s.fare) for s in valid]
            vals = {s.created_at.date(): f for s, f in zip(valid, fares)}
            c_date = (
                e.created_at.date() if hasattr(e.created_at, "date") else e.created_at
            )
            r37 = (
                compute_37_best(c_date, today, e.deadline, vals) if e.deadline else None
            )

            entries_data.append(
                {
                    "entry": {
                        "id": e.id,
                        "origin": e.origin,
                        "destination": e.destination,
                        "flightDate": e.flight_date.isoformat(),
                        "deadline": e.deadline.isoformat() if e.deadline else None,
                        "isActive": e.is_active,
                        "pastDeparture": e.flight_date < today,
                    },
                    "rule37Status": {
                        "phase": r37.phase.value,
                        "cutoffDate": r37.cutoff_date.isoformat(),
                        "historyBestVal": r37.history_best_val,
                        "latestVal": r37.latest_val,
                        "allTimeHigh": r37.all_time_high,
                        "allTimeLow": r37.all_time_low,
                    }
                    if r37
                    else None,
                    "minFare": min(fares, default=None),
                    "maxFare": max(fares, default=None),
                    "latestFare": vals.get(max(vals, default=None)),
                    "lastScraped": max(
                        e.price_snapshots, key=lambda s: s.created_at
                    ).created_at.isoformat()
                    if e.price_snapshots
                    else None,
                }
            )
        return render_inertia("List", props={"entries": entries_data})


@pages_bp.route("/create")
def create():
    return render_inertia("Create")


@pages_bp.route("/list")
def list_redirect():
    return redirect(url_for("pages.list_entries"))


@pages_bp.route("/detail/<entry_id>")
def detail_entry(entry_id):
    with SessionLocal() as db:
        if not (
            e := db.query(TrackingEntry).filter(TrackingEntry.id == entry_id).first()
        ):
            return redirect(url_for("pages.list_entries"))

        today = date.today()
        valid = [
            s for s in e.price_snapshots if s.scrape_status == "success" and s.fare
        ]
        fares = [float(s.fare) for s in valid]
        vals = {s.created_at.date(): f for s, f in zip(valid, fares)}
        c_date = e.created_at.date() if hasattr(e.created_at, "date") else e.created_at

        by_date = defaultdict(list)
        for s in e.price_snapshots:
            by_date[s.created_at.date()].append(s)

        daily = []
        for d, ss in sorted(by_date.items(), reverse=True):
            low = min(
                [s for s in ss if s.scrape_status == "success" and s.fare],
                key=lambda x: x.fare,
                default=None,
            )
            daily.append(
                {
                    "date": d.isoformat(),
                    "lowestFare": float(low.fare) if low else None,
                    "lowestSnapshot": {
                        "flightNumber": low.flight_number,
                        "fare": float(low.fare),
                    }
                    if low
                    else None,
                    "snapshots": [
                        {
                            "id": s.id,
                            "flightNumber": s.flight_number,
                            "departureAt": s.departure_at.isoformat()
                            if s.departure_at
                            else None,
                            "arrivalAt": s.arrival_at.isoformat()
                            if s.arrival_at
                            else None,
                            "fare": float(s.fare) if s.fare is not None else None,
                            "scrapeStatus": s.scrape_status,
                            "errorMessage": s.error_message,
                        }
                        for s in sorted(ss, key=lambda x: x.created_at, reverse=True)
                    ],
                }
            )

        r37 = compute_37_best(c_date, today, e.deadline, vals) if e.deadline else None

        return render_inertia(
            "Detail",
            props={
                "entry": {
                    "id": e.id,
                    "origin": e.origin,
                    "destination": e.destination,
                    "flightDate": e.flight_date.isoformat(),
                    "deadline": e.deadline.isoformat() if e.deadline else None,
                    "isActive": e.is_active,
                    "pastDeparture": e.flight_date < today,
                },
                "dailyGroups": daily,
                "today": today.isoformat(),
                "rule37Status": {
                    "phase": r37.phase.value,
                    "cutoffDate": r37.cutoff_date.isoformat(),
                    "historyBestVal": r37.history_best_val,
                    "latestVal": r37.latest_val,
                    "allTimeHigh": r37.all_time_high,
                    "allTimeLow": r37.all_time_low,
                }
                if r37
                else None,
                "allTimeLow": r37.all_time_low
                if r37
                else (min(fares, default=None) if fares else None),
                "allTimeHigh": r37.all_time_high
                if r37
                else (max(fares, default=None) if fares else None),
            },
        )
