import logging
from collections import defaultdict
from dataclasses import asdict
from datetime import date, datetime

from flask import Blueprint, redirect
from flask_inertia import render_inertia
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.extensions.database import FareSnapshot, Flight, Itinerary, db
from src.services.fx_rates import (
    FXRatesError,
    convert_amount,
    get_configured_base_currency,
)
from src.utils.rule37 import compute_37_best, compute_price_stats
from src.utils.transform import model_to_dict

logger = logging.getLogger(__name__)

flights_bp = Blueprint('flights', __name__, url_prefix='/flights')


def _serialize_snapshot(snapshot: FareSnapshot, currency: str) -> dict:
    if snapshot.scrape_status == 'success' and snapshot.fare is not None:
        try:
            snapshot.fare = convert_amount(
                snapshot.fare,
                snapshot.currency,
                currency,
            )
            snapshot.currency = currency
        except FXRatesError:
            logger.warning(
                'Failed to convert fare snapshot: snapshot_id=%s',
                snapshot.id,
            )

    return model_to_dict(snapshot)


def _get_combined_totals(itinerary: Itinerary, currency: str) -> dict[date, float]:
    date_fares = defaultdict(dict)
    for flight in itinerary.flights:
        for s in flight.fare_snapshots:
            if s.scrape_status == 'success' and s.fare is not None:
                src_currency = (s.currency or currency).upper()
                try:
                    fare_value = convert_amount(s.fare, src_currency, currency)
                except FXRatesError:
                    logger.warning(
                        'Failed to convert itinerary fare snapshot: snapshot_id=%s',
                        s.id,
                    )
                    continue

                s_date = (
                    s.created_at.date()
                    if isinstance(s.created_at, datetime)
                    else getattr(s.created_at, 'date', lambda: s.created_at)()
                )
                if (
                    flight.id not in date_fares[s_date]
                    or fare_value < date_fares[s_date][flight.id]
                ):
                    date_fares[s_date][flight.id] = fare_value

    combined_totals = {}
    num_flights = len(itinerary.flights)
    if num_flights == 0:
        return {}

    for d, f_fares in date_fares.items():
        if len(f_fares) == num_flights:
            combined_totals[d] = float(sum(f_fares.values()))

    return combined_totals


def _serialize_itinerary(itinerary: Itinerary, base_currency: str) -> dict:
    combined = _get_combined_totals(itinerary, base_currency)

    stats = compute_price_stats(combined)
    stats_dict = asdict(stats) if stats else None

    r37_dict = None
    if itinerary.deadline and combined:
        it_created_at = (
            itinerary.created_at.date()
            if isinstance(itinerary.created_at, datetime)
            else getattr(itinerary.created_at, 'date', lambda: itinerary.created_at)()
        )
        r37 = compute_37_best(it_created_at, date.today(), itinerary.deadline, combined)
        if r37:
            r37_dict = {**asdict(r37), 'phase': r37.phase.value}

    return {
        **model_to_dict(itinerary),
        'flights': [
            {
                **model_to_dict(f),
                'fare_snapshots': [_serialize_snapshot(s, base_currency) for s in f.fare_snapshots],
            }
            for f in itinerary.flights
        ],
        'statistics': stats_dict,
        'rule37_analysis': r37_dict,
    }


@flights_bp.route('/')
def index():
    base_currency = get_configured_base_currency()
    itineraries = (
        db.session.execute(
            select(Itinerary)
            .options(selectinload(Itinerary.flights).selectinload(Flight.fare_snapshots))
            .order_by(Itinerary.created_at)
        )
        .scalars()
        .unique()
        .all()
    )
    logger.debug('Rendered flights index: itineraries=%d', len(itineraries))

    return render_inertia(
        'Flights/Index',
        props={
            'itineraries': [_serialize_itinerary(it, base_currency) for it in itineraries],
            'base_currency': base_currency,
        },
    )


@flights_bp.route('/create')
def create():
    return render_inertia('Flights/Create')


@flights_bp.route('/<flight_id>')
def show(flight_id):
    try:
        base_currency = get_configured_base_currency()

        itinerary = db.session.execute(
            select(Itinerary)
            .options(selectinload(Itinerary.flights).selectinload(Flight.fare_snapshots))
            .where(Itinerary.id == flight_id)
        ).scalar_one_or_none()

        if not itinerary:
            logger.debug('Itinerary not found: id=%s', flight_id)
            return redirect('/flights/')

        return render_inertia(
            'Flights/Detail',
            props={
                'itinerary': _serialize_itinerary(itinerary, base_currency),
                'base_currency': base_currency,
            },
        )
    except Exception:
        logger.exception('Error rendering flights detail page: id=%s', flight_id)
        return redirect('/flights/')
