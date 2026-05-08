from datetime import date
from collections import defaultdict

from flask import Blueprint, redirect, render_template, url_for

from src.database import SessionLocal, TrackingEntry
from src.rule37 import compute_deadline_rule37

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
            rule37_status = compute_deadline_rule37(entry, snapshots, today)

            # Get latest successful fare (skip errors)
            successful_snapshots = sorted(
                [s for s in snapshots if s.scrape_status == "success" and s.fare],
                key=lambda s: s.scraped_at,
                reverse=True
            )
            latest_fare = float(successful_snapshots[0].fare) if successful_snapshots else None

            last_snap = max(snapshots, key=lambda s: s.scraped_at) if snapshots else None

            entries_data.append({
                "entry": entry,
                "rule37_status": rule37_status,
                "min_fare": min(successful_fares) if successful_fares else None,
                "max_fare": max(successful_fares) if successful_fares else None,
                "latest_fare": latest_fare,
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
        rule37_status = compute_deadline_rule37(entry, snapshots, today)

        # Compute all-time low and observation window min
        all_fares = [float(s.fare) for s in snapshots if s.scrape_status == "success" and s.fare]
        all_time_low = min(all_fares) if all_fares else None

        # Group snapshots by date (scraped_at.date())
        by_date = defaultdict(list)
        for snap in snapshots:
            day = snap.scraped_at.date()
            by_date[day].append(snap)

        # Build daily groups sorted by date (newest first)
        daily_groups = []
        for day in sorted(by_date.keys(), reverse=True):
            day_snapshots = by_date[day]
            # Find lowest price for this day
            successful = [s for s in day_snapshots if s.scrape_status == "success" and s.fare]
            lowest_snap = min(successful, key=lambda s: s.fare) if successful else None

            daily_groups.append({
                "date": day,
                "lowest_fare": float(lowest_snap.fare) if lowest_snap else None,
                "lowest_snapshot": lowest_snap,
                "snapshots": sorted(day_snapshots, key=lambda s: s.scraped_at, reverse=True),
            })

        return render_template(
            "detail.html",
            entry=entry,
            rule37_status=rule37_status,
            daily_groups=daily_groups,
            all_time_low=all_time_low,
            today=today,
        )
    finally:
        db.close()
