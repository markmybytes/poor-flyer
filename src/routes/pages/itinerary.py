import logging
from collections import defaultdict
from dataclasses import asdict
from datetime import date, datetime

from flask import Blueprint, g, make_response, redirect, request
from flask_inertia import render_inertia
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.extensions.database import FareSnapshot, Flight, Itinerary, db
from src.services.fx_rates import (
    FXRatesError,
    convert_amount,
    get_configured_base_currency,
)
from src.services.itinerary import create_itinerary
from src.utils.rule37 import compute_37_best, compute_price_stats
from src.utils.transform import model_to_dict

logger = logging.getLogger(__name__)

itineraries_bp = Blueprint('itineraries', __name__, url_prefix='/itineraries')


def _serialize_snapshot(snapshot: FareSnapshot, currency: str) -> dict:
    """Clones snapshot columns into a dict and applies currency translations safely."""
    data = model_to_dict(snapshot)
    if snapshot.scrape_status == 'success' and snapshot.fare is not None:
        try:
            data['fare'] = convert_amount(snapshot.fare, snapshot.currency, currency)
            data['currency'] = currency
        except FXRatesError:
            logger.warning('Failed to convert fare snapshot: snapshot_id=%s', snapshot.id)
    return data


def _get_combined_totals(itinerary: Itinerary, currency: str) -> dict[date, float]:
    """Computes daily combined price minimums across all legs of an itinerary."""
    date_fares = defaultdict(dict)
    for flight in itinerary.flights:
        for s in flight.fare_snapshots:
            if s.scrape_status == 'success' and s.fare is not None:
                src_currency = (s.currency or currency).upper()
                try:
                    fare_value = convert_amount(s.fare, src_currency, currency)
                except FXRatesError:
                    logger.warning(
                        'Failed to convert itinerary fare snapshot: snapshot_id=%s', s.id
                    )
                    continue

                s_date = (
                    s.created_at.date()
                    if isinstance(s.created_at, datetime)
                    else getattr(s.created_at, 'date', lambda s=s: s.created_at)()
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


def _serialize_itinerary(itinerary: Itinerary, base_currency: str, *, today: date) -> dict:
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
        r37 = compute_37_best(it_created_at, today, itinerary.deadline, combined)
        if r37:
            r37_dict = {**asdict(r37), 'phase': r37.phase.value}

    return model_to_dict(itinerary) | {
        'flights': [
            model_to_dict(f)
            | {'fare_snapshots': [_serialize_snapshot(s, base_currency) for s in f.fare_snapshots]}
            for f in itinerary.flights
        ],
        'statistics': stats_dict,
        'rule37_analysis': r37_dict,
    }


@itineraries_bp.route('/')
def index():
    base_currency = get_configured_base_currency()
    archived_filter = (
        Itinerary.archived_at.is_not(None)
        if request.args.get('archived') == '1'
        else Itinerary.archived_at.is_(None)
    )
    itineraries = (
        db.session.execute(
            select(Itinerary)
            .options(selectinload(Itinerary.flights).selectinload(Flight.fare_snapshots))
            .where(archived_filter)
            .order_by(Itinerary.created_at)
        )
        .scalars()
        .unique()
        .all()
    )
    logger.debug('Rendered itineraries index: itineraries=%d', len(itineraries))
    return render_inertia(
        'Itineraries/Index',
        props={
            'itineraries': [
                _serialize_itinerary(it, base_currency, today=datetime.now(g.tz).date())
                for it in itineraries
            ],
            'base_currency': base_currency,
        },
    )


@itineraries_bp.route('/create')
def create():
    return render_inertia('Itineraries/Create')


@itineraries_bp.route('', methods=['POST'])
def create_submit():
    data = request.get_json(silent=True) or request.form.to_dict()
    try:
        itinerary = create_itinerary(data)
        db.session.commit()
    except (KeyError, TypeError, ValueError) as exc:
        db.session.rollback()
        logger.warning('Invalid itinerary submission: %s', exc)
        response = make_response(
            render_inertia(
                'Itineraries/Create',
                props={'errors': {'itinerary': '請檢查輸入內容'}},
            )
        )
        response.status_code = 422
        return response

    logger.info('Created itinerary from page form: id=%s', itinerary.id)
    return redirect('/')


@itineraries_bp.route('/<itinerary_id>')
def show(itinerary_id):
    try:
        base_currency = get_configured_base_currency()
        itinerary = db.session.execute(
            select(Itinerary)
            .options(selectinload(Itinerary.flights).selectinload(Flight.fare_snapshots))
            .where(Itinerary.id == itinerary_id)
        ).scalar_one_or_none()
        if not itinerary:
            logger.debug('Itinerary not found: id=%s', itinerary_id)
            return redirect('/itineraries/')
        return render_inertia(
            'Itineraries/Detail',
            props={
                'itinerary': _serialize_itinerary(
                    itinerary, base_currency, today=datetime.now(g.tz).date()
                ),
                'base_currency': base_currency,
            },
        )
    except Exception:
        logger.exception('Error rendering itineraries detail page: id=%s', itinerary_id)
        return redirect('/itineraries/')
