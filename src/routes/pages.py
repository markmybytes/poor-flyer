from datetime import date

from flask import Blueprint, redirect, render_template, url_for

from src.database import SessionLocal, TrackingEntry
from src.rule37 import compute_deadline_rule37, compute_dynamic_rule37

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def list_entries():
    db = SessionLocal()
    try:
        today = date.today()
        entries = db.query(TrackingEntry).order_by(TrackingEntry.flight_date).all()
        entries_data = []

        for entry in entries:
            snapshots = entry.price_snapshots
            successful_fares = [
                float(s.fare) for s in snapshots if s.scrape_status == "success" and s.fare
            ]
            deadline_status = compute_deadline_rule37(entry, snapshots, today)
            dynamic_status = compute_dynamic_rule37(snapshots)
            last_snap = max(snapshots, key=lambda s: s.scraped_at) if snapshots else None

            entries_data.append({
                "entry": entry,
                "deadline_status": deadline_status,
                "dynamic_status": dynamic_status,
                "min_fare": min(successful_fares) if successful_fares else None,
                "max_fare": max(successful_fares) if successful_fares else None,
                "last_scraped": last_snap.scraped_at if last_snap else None,
                "past_departure": entry.flight_date < today,
            })

        return render_template("list.html", entries=entries_data, today=today)
    finally:
        db.close()


@pages_bp.route("/create")
def create():
    return render_template("create.html")


@pages_bp.route("/list")
def list_redirect():
    return redirect(url_for("pages.list_entries"))


@pages_bp.route("/detail/<entry_id>")
def detail_entry(entry_id):
    db = SessionLocal()
    try:
        today = date.today()
        entry = db.query(TrackingEntry).filter(TrackingEntry.id == entry_id).first()
        if not entry:
            return redirect(url_for("pages.list_entries"))

        snapshots = entry.price_snapshots
        deadline_status = compute_deadline_rule37(entry, snapshots, today)
        dynamic_status = compute_dynamic_rule37(snapshots)

        successful_ordered = sorted(
            [s for s in snapshots if s.scrape_status == "success"],
            key=lambda s: s.scraped_at,
        )
        observation_ids = {s.id for s in successful_ordered[: dynamic_status.observation_count]}

        # Build table rows (newest first) with ORM objects for Jinja
        table_rows = []
        for snap in sorted(snapshots, key=lambda s: s.scraped_at, reverse=True):
            table_rows.append({
                "snap": snap,
                "is_dynamic_observation": snap.id in observation_ids,
            })

        # Build chart data (oldest first, JSON-serializable)
        chart_data = []
        for snap in sorted(snapshots, key=lambda s: s.scraped_at):
            if snap.scrape_status == "success" and snap.fare:
                chart_data.append({
                    "date": snap.scraped_at.strftime("%Y-%m-%d"),
                    "fare": float(snap.fare),
                    "is_observation": snap.id in observation_ids,
                })

        return render_template(
            "detail.html",
            entry=entry,
            deadline_status=deadline_status,
            dynamic_status=dynamic_status,
            table_rows=table_rows,
            chart_data=chart_data,
            today=today,
        )
    finally:
        db.close()
