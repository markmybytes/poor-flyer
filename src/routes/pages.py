from collections import defaultdict
from datetime import date

from flask import Blueprint, redirect, render_template, url_for

from src.database import SessionLocal, TrackingEntry
from src.rule37 import compute_37_best

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def list_entries():
    with SessionLocal() as db:
        today, entries_data = date.today(), []
        for e in db.query(TrackingEntry).order_by(TrackingEntry.flight_date).all():
            valid = [
                s for s in e.price_snapshots if s.scrape_status == "success" and s.fare
            ]
            fares = [float(s.fare) for s in valid]
            vals = {s.created_at.date(): f for s, f in zip(valid, fares)}
            c_date = (
                e.created_at.date() if hasattr(e.created_at, "date") else e.created_at
            )

            entries_data.append(
                {
                    "entry": e,
                    "rule37_status": compute_37_best(c_date, today, e.deadline, vals)
                    if e.deadline
                    else None,
                    "min_fare": min(fares, default=None),
                    "max_fare": max(fares, default=None),
                    "latest_fare": vals.get(max(vals, default=None)),
                    "last_scraped": max(
                        e.price_snapshots, key=lambda s: s.created_at
                    ).created_at
                    if e.price_snapshots
                    else None,
                    "past_departure": e.flight_date < today,
                }
            )
        return render_template("list.html", entries=entries_data, today=today)


@pages_bp.route("/create")
def create():
    return render_template("create.html")


@pages_bp.route("/list")
def list_redirect():
    return redirect(url_for("pages.list_entries"))


@pages_bp.route("/detail/<entry_id>")
def detail_entry(entry_id):
    with SessionLocal() as db:
        # Fetch entry with walrus operator, aborting early if missing
        if not (
            e := db.query(TrackingEntry).filter(TrackingEntry.id == entry_id).first()
        ):
            return redirect(url_for("pages.list_entries"))

        valid = [
            s for s in e.price_snapshots if s.scrape_status == "success" and s.fare
        ]
        fares = [float(s.fare) for s in valid]
        vals = {s.created_at.date(): f for s, f in zip(valid, fares)}
        c_date = e.created_at.date() if hasattr(e.created_at, "date") else e.created_at

        by_date = defaultdict(list)
        for s in e.price_snapshots:
            by_date[s.created_at.date()].append(s)

        # Unrolled back to a standard loop for scope safety and runtime stability
        daily = []
        for d, ss in sorted(by_date.items(), reverse=True):
            low = min(
                [s for s in ss if s.scrape_status == "success" and s.fare],
                key=lambda x: x.fare,
                default=None,
            )
            daily.append(
                {
                    "date": d,
                    "lowest_fare": float(low.fare) if low else None,
                    "lowest_snapshot": low,
                    "snapshots": sorted(ss, key=lambda x: x.created_at, reverse=True),
                }
            )

        return render_template(
            "detail.html",
            entry=e,
            daily_groups=daily,
            today=date.today(),
            rule37_status=compute_37_best(c_date, date.today(), e.deadline, vals)
            if e.deadline
            else None,
            all_time_low=min(fares, default=None),
        )
