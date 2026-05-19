from dataclasses import asdict
from datetime import date

from flask import Blueprint, redirect
from flask_inertia import render_inertia
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.extensions.database import Flight, db
from src.services.rule37 import compute_37_best
from src.utils.transform import model_to_dict

flights_bp = Blueprint('flights', __name__, url_prefix='/flights')


def _r37(flight: Flight) -> dict | None:
    if not flight.deadline:
        return None
    r37 = compute_37_best(
        getattr(flight.created_at, 'date', lambda: flight.created_at)(),
        date.today(),
        flight.deadline,
        {
            s.created_at.date(): float(s.fare)
            for s in flight.fare_snapshots
            if s.scrape_status == 'success' and s.fare
        },
    )
    return {**asdict(r37), 'phase': r37.phase.value}


@flights_bp.route('/')
def index():
    flights = (
        db.session.execute(
            select(Flight).options(selectinload(Flight.fare_snapshots)).order_by(Flight.flight_date)
        )
        .scalars()
        .all()
    )

    return render_inertia(
        'Flights/Index',
        props={
            'flights': [
                {
                    **model_to_dict(f),
                    'fare_snapshots': f.fare_snapshots,
                    'rule37_analysis': _r37(f),
                }
                for f in flights
            ]
        },
    )


@flights_bp.route('/create')
def create():
    return render_inertia('Flights/Create')


@flights_bp.route('/<flight_id>')
def show(flight_id):
    flight = db.session.execute(
        select(Flight).options(selectinload(Flight.fare_snapshots)).where(Flight.id == flight_id)
    ).scalar_one_or_none()

    if not flight:
        return redirect('/flights/')
    return render_inertia(
        'Flights/Detail',
        props={
            'flight': {
                **model_to_dict(flight),
                'rule37_analysis': _r37(flight),
            }
        },
    )
