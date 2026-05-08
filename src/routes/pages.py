from datetime import date

from flask import Blueprint, redirect, render_template, url_for
from sqlalchemy.orm import Session

from src.database import SessionLocal, TrackingEntry
from src.rule37 import compute_rule37

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def create():
    return render_template("create.html")


@pages_bp.route("/list")
def list_entries():
    db = SessionLocal()
    try:
        entries = db.query(TrackingEntry).all()
        entries_with_status = []

        for entry in entries:
            status = compute_rule37(entry, entry.price_snapshots, date.today())
            entries_with_status.append(
                {
                    "entry": entry,
                    "status": status,
                }
            )

        return render_template("list.html", entries=entries_with_status)
    finally:
        db.close()


@pages_bp.route("/detail/<entry_id>")
def detail_entry(entry_id):
    db = SessionLocal()
    try:
        entry = db.query(TrackingEntry).filter(TrackingEntry.id == entry_id).first()
        if not entry:
            return redirect(url_for("pages.list_entries"))

        status = compute_rule37(entry, entry.price_snapshots, date.today())

        snapshots_with_type = []
        if entry.rule_mode == "fixed_window":
            from datetime import datetime

            cutoff_datetime = datetime.combine(
                entry.monitor_start + (entry.monitor_end - entry.monitor_start) * 0.37,
                datetime.min.time(),
            )
            for snap in sorted(
                entry.price_snapshots, key=lambda s: s.scraped_at, reverse=True
            ):
                snapshots_with_type.append(
                    {
                        "snapshot": snap,
                        "is_observation": snap.scraped_at < cutoff_datetime
                        and snap.scrape_status == "success",
                    }
                )
        else:
            sample_size = entry.rule_sample_size
            observation_count = int(sample_size * 0.37)
            successful = sorted(
                [s for s in entry.price_snapshots if s.scrape_status == "success"],
                key=lambda s: s.scraped_at,
            )
            for snap in sorted(
                entry.price_snapshots, key=lambda s: s.scraped_at, reverse=True
            ):
                is_observation = (
                    snap.scrape_status == "success"
                    and len([s for s in successful if s.scraped_at <= snap.scraped_at])
                    <= observation_count
                )
                snapshots_with_type.append(
                    {
                        "snapshot": snap,
                        "is_observation": is_observation,
                    }
                )

        return render_template(
            "detail.html", entry=entry, status=status, snapshots=snapshots_with_type
        )
    finally:
        db.close()
