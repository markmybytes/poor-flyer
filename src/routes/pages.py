from dataclasses import asdict
from datetime import date

from flask import Blueprint, redirect, url_for
from flask_inertia import render_inertia
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.database import Flight, SessionLocal
from src.services.rule37 import compute_37_best

pages_bp = Blueprint("pages", __name__)


def _get_r37_analysis(flight: Flight) -> dict | None:
    """Helper to compute Rule 37 analysis from a flight's snapshots."""
    if not flight.deadline:
        return None

    r37 = compute_37_best(
        getattr(flight.created_at, "date", lambda: flight.created_at)(),
        date.today(),
        flight.deadline,
        {
            s.created_at.date(): float(s.fare)
            for s in flight.fare_snapshots
            if s.scrape_status == "success" and s.fare
        },
    )

    return {**asdict(r37), "phase": r37.phase.value}


@pages_bp.route("/")
def list_entries():
    with SessionLocal() as db:
        flights = (
            db.execute(
                select(Flight)
                .options(selectinload(Flight.fare_snapshots))
                .order_by(Flight.flight_date)
            )
            .scalars()
            .all()
        )

    entries = [
        {
            "id": f.id,
            "origin": f.origin,
            "destination": f.destination,
            "flight_date": f.flight_date,
            "deadline": f.deadline,
            "is_active": f.is_active,
            "created_at": f.created_at,
            "fare_snapshots": f.fare_snapshots,
            "rule37_analysis": _get_r37_analysis(f),
        }
        for f in flights
    ]
    return render_inertia("List", props={"flights": entries})


@pages_bp.route("/create")
def create():
    return render_inertia("Create")


@pages_bp.route("/detail/<entry_id>")
def detail_entry(entry_id):
    with SessionLocal() as db:
        f = db.execute(
            select(Flight)
            .options(selectinload(Flight.fare_snapshots))
            .where(Flight.id == entry_id)
        ).scalar_one_or_none()

    if not f:
        return redirect(url_for("pages.list_entries"))

    return render_inertia(
        "Detail",
        props={
            "flight": {
                "id": f.id,
                "origin": f.origin,
                "destination": f.destination,
                "flight_date": f.flight_date,
                "deadline": f.deadline,
                "is_active": f.is_active,
                "fare_snapshots": f.fare_snapshots,
                "rule37_analysis": _get_r37_analysis(f),
            },
        },
    )
