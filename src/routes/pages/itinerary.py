import logging
from dataclasses import asdict
from datetime import UTC, date, datetime
from typing import Any
from urllib.parse import urlsplit

from flask import Blueprint, flash, g, redirect, request, session
from flask.typing import ResponseReturnValue
from flask_inertia import render_inertia
from fli.models.airline import AIRLINE_NAMES
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.extensions.database import FareSnapshot, Flight, Itinerary, db
from src.services.fx_rates import (
    FXRatesError,
    convert_amount,
    get_configured_base_currency,
)
from src.services.itinerary import (
    create_itinerary,
    get_combined_totals,
    validate_deadline,
)
from src.utils.filters import parse_bool
from src.utils.rule37 import compute_37_best, compute_price_stats
from src.utils.transform import model_to_dict

logger = logging.getLogger(__name__)

itineraries_bp = Blueprint('itineraries', __name__, url_prefix='/itineraries')

_STATUS_FIELDS = frozenset({'is_active', 'archived'})


def _safe_back_url(fallback: str) -> str:
    """Land the flash on the page that sent the toggle, never on another origin."""
    referrer = request.referrer
    if not referrer:
        return fallback

    parts = urlsplit(referrer)
    if parts.scheme not in ('', 'http', 'https') or parts.netloc not in ('', request.host):
        return fallback
    if not parts.path.startswith('/') or parts.path.startswith('//'):
        return fallback
    return f'{parts.path}?{parts.query}' if parts.query else parts.path


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


def _parse_deadline(raw: Any) -> date | None:
    """Parse a page deadline; an empty value clears it."""
    if not raw:
        return None
    try:
        return datetime.strptime(str(raw), '%Y-%m-%d').date()
    except ValueError:
        raise ValueError('Deadline must be a valid date') from None


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
def create_submit() -> ResponseReturnValue:
    try:
        itinerary = create_itinerary(
            request.get_json(silent=True) or request.form.to_dict(),
            today=datetime.now(g.tz).date(),
        )
        db.session.commit()
        logger.info('created itinerary from page form: id=%s', itinerary.id)

        flash('已成功建立票價追蹤', 'success')
        return redirect('/')
    except (KeyError, TypeError, ValueError) as exc:
        db.session.rollback()
        logger.info('invalid itinerary submission: error=%s', exc)

        session['errors'] = {'itinerary': '請檢查輸入內容'}
        return redirect('/itineraries/create')


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
def update_itinerary(itinerary_id: str) -> ResponseReturnValue:
    itinerary = db.session.execute(
        select(Itinerary).where(Itinerary.id == itinerary_id)
    ).scalar_one_or_none()

    if not itinerary:
        logger.debug('itinerary not found for update: id=%s', itinerary_id)
        return redirect('/itineraries/')

    data = request.get_json(silent=True) or request.form.to_dict()
    errors: dict[str, str] = {}

    if 'deadline' in data:
        try:
            deadline = _parse_deadline(data['deadline'])
            validate_deadline(
                deadline,
                itinerary.flights[0].flight_date if itinerary.flights else None,
                today=datetime.now(g.tz).date(),
            )
        except ValueError as exc:
            errors['deadline'] = str(exc)
        else:
            itinerary.deadline = deadline

    if 'notify_per_leg' in data:
        try:
            itinerary.notify_per_leg = parse_bool(data['notify_per_leg'], 'notify_per_leg')
        except ValueError as exc:
            errors['notify_per_leg'] = str(exc)

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
def update_status(itinerary_id: str) -> ResponseReturnValue:
    itinerary = db.session.execute(
        select(Itinerary).where(Itinerary.id == itinerary_id)
    ).scalar_one_or_none()

    if not itinerary:
        logger.debug('itinerary not found for status update: id=%s', itinerary_id)
        return redirect('/itineraries/')

    data = request.get_json(silent=True) or request.form.to_dict()
    target = _safe_back_url(f'/itineraries/{itinerary_id}')

    if unsupported := sorted(set(data) - _STATUS_FIELDS):
        logger.info(
            'rejected itinerary status update: id=%s fields=%s',
            itinerary_id,
            ','.join(unsupported),
        )
        session['errors'] = {'status': f'Unsupported field: {", ".join(unsupported)}'}
        return redirect(target)

    archived = None
    try:
        if 'is_active' in data:
            itinerary.is_active = parse_bool(data['is_active'], 'is_active')
        if 'archived' in data:
            archived = parse_bool(data['archived'], 'archived')
            if archived:
                if itinerary.archived_at is None:
                    itinerary.archived_at = datetime.now(UTC)
            else:
                itinerary.archived_at = None
    except ValueError as exc:
        db.session.rollback()
        logger.info('invalid itinerary status update: id=%s error=%s', itinerary_id, exc)
        session['errors'] = {'status': str(exc)}
        return redirect(target)

    db.session.commit()
    logger.info('updated itinerary status: id=%s fields=%s', itinerary_id, ','.join(sorted(data)))

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
