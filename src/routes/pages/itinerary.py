import logging
from dataclasses import asdict
from datetime import UTC, date, datetime

from flask import Blueprint, flash, g, redirect, request, session
from flask.typing import ResponseReturnValue
from flask_inertia import render_inertia
from fli.models.airline import AIRLINE_NAMES
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.extensions.database import FareSnapshot, Flight, Itinerary, db
from src.schemas.itinerary import ItineraryCreate, ItinerarySettings, ItineraryStatus
from src.schemas.validators import date_cmp
from src.services.fx_rates import (
    FXRatesError,
    convert_amount,
    get_configured_base_currency,
)
from src.services.itinerary import create_itinerary, get_combined_totals
from src.utils.rule37 import compute_37_best, compute_price_stats
from src.utils.transform import model_to_dict
from src.validation import back_url, validated

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
            logger.warning('convert fare snapshot failed: snapshot_id=%s', snapshot.id)
    return data


def _serialize_itinerary(
    itinerary: Itinerary,
    base_currency: str,
    *,
    today: date,
    include_rule37: bool = True,
) -> dict:
    combined = get_combined_totals(itinerary, base_currency)
    stats_dict = asdict(stats) if (stats := compute_price_stats(combined)) else None
    r37_dict = None

    if include_rule37 and itinerary.deadline and combined:
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
def index() -> ResponseReturnValue:
    base_currency = get_configured_base_currency()
    archived_view = request.args.get('archived') == '1'

    itineraries = (
        db.session.execute(
            select(Itinerary)
            .options(selectinload(Itinerary.flights).selectinload(Flight.fare_snapshots))
            .where(
                Itinerary.archived_at.is_not(None)
                if archived_view
                else Itinerary.archived_at.is_(None)
            )
            .order_by(Itinerary.created_at)
        )
        .scalars()
        .unique()
        .all()
    )

    logger.debug('rendered itineraries index: itineraries=%d', len(itineraries))
    return render_inertia(
        'Itineraries/Index',
        props={
            'itineraries': [
                _serialize_itinerary(
                    it,
                    base_currency,
                    today=datetime.now(g.tz).date(),
                    include_rule37=not archived_view,
                )
                for it in itineraries
            ],
            'base_currency': base_currency,
        },
    )


@itineraries_bp.route('/create')
def create() -> ResponseReturnValue:
    return render_inertia(
        'Itineraries/Create',
        props={
            'airlines': sorted(
                (
                    {'code': code.removeprefix('_'), 'name': name}
                    for code, name in AIRLINE_NAMES.items()
                ),
                key=lambda airline: airline['code'],
            )
        },
    )


@itineraries_bp.route('', methods=['POST'])
@validated(ItineraryCreate, redirect_to='/itineraries/create')
def create_submit() -> ResponseReturnValue:
    payload: ItineraryCreate = g.validated
    try:
        itinerary = create_itinerary(
            payload.model_dump(mode='json', exclude_unset=True),
            today=datetime.now(g.tz).date(),
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    logger.info('created itinerary from page form: id=%s', itinerary.id)

    flash('已成功建立票價追蹤', 'success')
    return redirect('/')


@itineraries_bp.route('/<itinerary_id>')
def show(itinerary_id: str) -> ResponseReturnValue:
    try:
        base_currency = get_configured_base_currency()
        itinerary = db.session.execute(
            select(Itinerary)
            .options(selectinload(Itinerary.flights).selectinload(Flight.fare_snapshots))
            .where(Itinerary.id == itinerary_id)
        ).scalar_one_or_none()

        if not itinerary:
            logger.debug('itinerary not found: id=%s', itinerary_id)
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
        logger.exception('render itinerary detail failed: id=%s', itinerary_id)
        return redirect('/itineraries/')


@itineraries_bp.route('/<itinerary_id>', methods=['PATCH'])
@validated(ItinerarySettings, redirect_to='/itineraries/{itinerary_id}')
def update_itinerary(itinerary_id: str) -> ResponseReturnValue:
    itinerary = db.session.execute(
        select(Itinerary).where(Itinerary.id == itinerary_id)
    ).scalar_one_or_none()

    if not itinerary:
        logger.debug('itinerary not found for update: id=%s', itinerary_id)
        return redirect('/itineraries/')

    payload: ItinerarySettings = g.validated
    errors: dict[str, str] = {}

    if 'deadline' in payload.model_fields_set:
        if payload.deadline is None:
            itinerary.deadline = None
        else:
            first_departure = itinerary.flights[0].flight_date if itinerary.flights else None
            try:
                date_cmp(
                    payload.deadline,
                    datetime.now(g.tz).date(),
                    op='ge',
                    copy='購票限期不能早於今天',
                )
                if first_departure is not None:
                    date_cmp(
                        payload.deadline,
                        first_departure,
                        op='le',
                        copy='購票限期不能晚於首程出發日期',
                    )
            except ValueError as exc:
                errors['deadline'] = str(exc)
            else:
                itinerary.deadline = payload.deadline

    if 'notify_per_leg' in payload.model_fields_set:
        itinerary.notify_per_leg = payload.notify_per_leg

    if errors:
        db.session.rollback()
        logger.info('invalid itinerary update: id=%s fields=%s', itinerary_id, ','.join(errors))

        session['errors'] = errors
        return redirect(f'/itineraries/{itinerary_id}')

    db.session.commit()
    logger.info('updated itinerary from page form: id=%s', itinerary_id)

    flash('已更新設定', 'success')
    return redirect(f'/itineraries/{itinerary_id}')


@itineraries_bp.route('/<itinerary_id>/status', methods=['PATCH'])
@validated(ItineraryStatus, redirect_to='/itineraries/{itinerary_id}')
def update_status(itinerary_id: str) -> ResponseReturnValue:
    itinerary = db.session.execute(
        select(Itinerary).where(Itinerary.id == itinerary_id)
    ).scalar_one_or_none()

    if not itinerary:
        logger.debug('itinerary not found for status update: id=%s', itinerary_id)
        return redirect('/itineraries/')

    payload: ItineraryStatus = g.validated
    target = back_url(f'/itineraries/{itinerary_id}')

    if 'is_active' in payload.model_fields_set:
        itinerary.is_active = payload.is_active

    archived = None
    if 'archived' in payload.model_fields_set:
        archived = payload.archived
        if archived:
            if itinerary.archived_at is None:
                itinerary.archived_at = datetime.now(UTC)
        else:
            itinerary.archived_at = None

    db.session.commit()
    logger.info(
        'updated itinerary status: id=%s fields=%s',
        itinerary_id,
        ','.join(sorted(payload.model_fields_set)),
    )

    if archived is True:
        flash('已封存', 'success')
    elif archived is False:
        flash('已恢復追蹤', 'success')
    return redirect(target)


@itineraries_bp.route('/<itinerary_id>', methods=['DELETE'])
def delete_itinerary(itinerary_id: str) -> ResponseReturnValue:
    itinerary = db.session.execute(
        select(Itinerary).where(Itinerary.id == itinerary_id)
    ).scalar_one_or_none()

    if not itinerary:
        logger.debug('itinerary not found for deletion: id=%s', itinerary_id)
        return redirect('/itineraries/')

    db.session.delete(itinerary)
    db.session.commit()

    logger.info('deleted itinerary from page form: id=%s', itinerary_id)
    return redirect('/itineraries/')
