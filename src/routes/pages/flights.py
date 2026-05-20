from collections import defaultdict
from dataclasses import asdict
from datetime import date, datetime

from flask import Blueprint, redirect
from flask_inertia import render_inertia
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.extensions.database import Flight, Itinerary, db
from src.services.rule37 import compute_37_best
from src.utils.transform import model_to_dict

flights_bp = Blueprint('flights', __name__, url_prefix='/flights')


def _r37(itinerary: Itinerary) -> dict | None:
    if not itinerary.deadline:
        return None

    date_fares = defaultdict(dict)
    for flight in itinerary.flights:
        for s in flight.fare_snapshots:
            if s.scrape_status == 'success' and s.fare:
                s_date = s.created_at.date() if isinstance(s.created_at, datetime) else getattr(s.created_at, 'date', lambda: s.created_at)()
                if flight.id not in date_fares[s_date] or s.fare < date_fares[s_date][flight.id]:
                    date_fares[s_date][flight.id] = s.fare

    combined_totals = {}
    num_flights = len(itinerary.flights)
    if num_flights == 0:
        return None

    for d, f_fares in date_fares.items():
        if len(f_fares) == num_flights:
            combined_totals[d] = float(sum(f_fares.values()))

    if not combined_totals:
        return None

    it_created_at = itinerary.created_at.date() if isinstance(itinerary.created_at, datetime) else getattr(itinerary.created_at, 'date', lambda: itinerary.created_at)()

    r37 = compute_37_best(
        it_created_at,
        date.today(),
        itinerary.deadline,
        combined_totals,
    )
    return {**asdict(r37), 'phase': r37.phase.value}


@flights_bp.route('/')
def index():
    itineraries = (
        db.session.execute(
            select(Itinerary).options(selectinload(Itinerary.flights).selectinload(Flight.fare_snapshots)).order_by(Itinerary.created_at)
        )
        .scalars()
        .unique()
        .all()
    )

    return render_inertia(
        'Flights/Index',
        props={
            'itineraries': [
                {
                    **model_to_dict(itinerary),
                    'flights': [
                        {
                            **model_to_dict(f),
                            'fare_snapshots': f.fare_snapshots,
                        }
                        for f in itinerary.flights
                    ],
                    'rule37_analysis': _r37(itinerary),
                }
                for itinerary in itineraries
            ]
        },
    )


@flights_bp.route('/create')
def create():
    return render_inertia('Flights/Create')


@flights_bp.route('/<flight_id>')
def show(flight_id):
    itinerary = db.session.execute(
        select(Itinerary).options(selectinload(Itinerary.flights).selectinload(Flight.fare_snapshots)).where(Itinerary.id == flight_id)
    ).scalar_one_or_none()

    if not itinerary:
        return redirect('/flights/')
    return render_inertia(
        'Flights/Detail',
        props={
            'itinerary': {
                **model_to_dict(itinerary),
                'flights': [
                    {
                        **model_to_dict(f),
                        'fare_snapshots': f.fare_snapshots,
                    }
                    for f in itinerary.flights
                ],
                'rule37_analysis': _r37(itinerary),
            }
        },
    )
