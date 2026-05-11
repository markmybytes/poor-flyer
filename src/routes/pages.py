from dataclasses import asdict
from datetime import date

from flask import Blueprint, redirect, url_for
from flask_inertia import render_inertia

from src.database import Flight, SessionLocal
from src.services.rule37 import compute_37_best

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def list_entries():
    with SessionLocal() as db:
        today = date.today()
        entries_data = []
        for f in db.query(Flight).order_by(Flight.flight_date).all():
            valid = [
                s for s in f.fare_snapshots if s.scrape_status == "success" and s.fare
            ]
            fares = [float(s.fare) for s in valid]
            vals = {s.created_at.date(): f for s, f in zip(valid, fares)}
            c_date = (
                f.created_at.date() if hasattr(f.created_at, "date") else f.created_at
            )
            r37 = (
                compute_37_best(c_date, today, f.deadline, vals) if f.deadline else None
            )

            entries_data.append(
                {
                    "id": f.id,
                    "origin": f.origin,
                    "destination": f.destination,
                    "flightDate": f.flight_date.isoformat(),
                    "deadline": f.deadline.isoformat() if f.deadline else None,
                    "isActive": f.is_active,
                    "createdAt": f.created_at.isoformat(),
                    "fareSnapshots": [
                        {
                            "id": s.id,
                            "fare": float(s.fare) if s.fare else None,
                            "scrapeStatus": s.scrape_status,
                            "createdAt": s.created_at.isoformat(),
                        }
                        for s in f.fare_snapshots
                    ],
                    "rule37Analysis": (
                        {**asdict(r37), "phase": r37.phase.value} if r37 else None
                    ),
                }
            )
        return render_inertia("List", props={"flights": entries_data})


@pages_bp.route("/create")
def create():
    return render_inertia("Create")


@pages_bp.route("/detail/<entry_id>")
def detail_entry(entry_id):
    with SessionLocal() as db:
        if not (f := db.query(Flight).filter(Flight.id == entry_id).first()):
            return redirect(url_for("pages.list_entries"))

        today = date.today()
        valid = [s for s in f.fare_snapshots if s.scrape_status == "success" and s.fare]
        fares = [float(s.fare) for s in valid]
        vals = {s.created_at.date(): f for s, f in zip(valid, fares)}
        c_date = f.created_at.date() if hasattr(f.created_at, "date") else f.created_at
        r37 = compute_37_best(c_date, today, f.deadline, vals) if f.deadline else None

        return render_inertia(
            "Detail",
            props={
                "flight": {
                    "id": f.id,
                    "origin": f.origin,
                    "destination": f.destination,
                    "flightDate": f.flight_date.isoformat(),
                    "deadline": f.deadline.isoformat() if f.deadline else None,
                    "isActive": f.is_active,
                },
                "fareSnapshots": [
                    {
                        "id": s.id,
                        "flightNumber": s.flight_number,
                        "departureAt": (
                            s.departure_at.isoformat() if s.departure_at else None
                        ),
                        "arrivalAt": s.arrival_at.isoformat() if s.arrival_at else None,
                        "fare": float(s.fare) if s.fare else None,
                        "scrapeStatus": s.scrape_status,
                        "errorMessage": s.error_message,
                        "createdAt": s.created_at.isoformat(),
                    }
                    for s in f.fare_snapshots
                ],
                "rule37Analysis": (
                    {**asdict(r37), "phase": r37.phase.value} if r37 else None
                ),
            },
        )
