from collections import defaultdict
from datetime import date

from flask import Blueprint, redirect, url_for
from flask_inertia import render_inertia
from src.backend.database import SessionLocal, TrackingEntry
from src.backend.services.rule37 import DeadlineRule37, compute_37_best

pages_bp = Blueprint("pages", __name__)


def _serialize_entry(e: TrackingEntry, today: date | None = None) -> dict:
    data = {
        "id": e.id,
        "origin": e.origin,
        "destination": e.destination,
        "flight_date": e.flight_date.isoformat(),
        "deadline": e.deadline.isoformat() if e.deadline else None,
        "is_active": e.is_active,
        "past_departure": e.flight_date < today if today else False,
    }
    return data


def _serialize_rule37(r: DeadlineRule37 | None) -> dict | None:
    if r is None:
        return None
    return {
        "phase": r.phase.value,
        "cutoff_date": r.cutoff_date.isoformat(),
        "history_best_val": r.history_best_val,
        "latest_val": r.latest_val,
        "all_time_high": r.all_time_high,
        "all_time_low": r.all_time_low,
    }


def _serialize_snapshot(s) -> dict:
    return {
        "id": s.id,
        "flight_number": s.flight_number,
        "departure_at": s.departure_at.isoformat() if s.departure_at else None,
        "arrival_at": s.arrival_at.isoformat() if s.arrival_at else None,
        "fare": float(s.fare) if s.fare is not None else None,
        "scrape_status": s.scrape_status,
        "error_message": s.error_message,
    }


@pages_bp.route("/")
def list_entries():
    print("Rendering list page")
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
            rule37 = (
                compute_37_best(c_date, today, e.deadline, vals) if e.deadline else None
            )

            entries_data.append(
                {
                    "entry": _serialize_entry(e, today),
                    "rule37_status": _serialize_rule37(rule37),
                    "min_fare": min(fares, default=None),
                    "max_fare": max(fares, default=None),
                    "latest_fare": vals.get(max(vals, default=None)),
                    "last_scraped": (
                        max(
                            e.price_snapshots, key=lambda s: s.created_at
                        ).created_at.isoformat()
                        if e.price_snapshots
                        else None
                    ),
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
                    "lowest_fare": float(low.fare) if low else None,
                    "lowest_snapshot": (
                        {"flight_number": low.flight_number, "fare": float(low.fare)}
                        if low
                        else None
                    ),
                    "snapshots": [
                        _serialize_snapshot(s)
                        for s in sorted(ss, key=lambda x: x.created_at, reverse=True)
                    ],
                }
            )

        rule37_data = (
            compute_37_best(c_date, today, e.deadline, vals) if e.deadline else None
        )

        all_time_high = (
            rule37_data.all_time_high
            if rule37_data
            else (max(fares, default=None) if fares else None)
        )
        all_time_low = (
            rule37_data.all_time_low
            if rule37_data
            else (min(fares, default=None) if fares else None)
        )

        return render_inertia(
            "Detail",
            props={
                "entry": _serialize_entry(e, today),
                "daily_groups": daily,
                "today": today.isoformat(),
                "rule37_status": _serialize_rule37(rule37_data),
                "all_time_low": all_time_low,
                "all_time_high": all_time_high,
            },
        )
