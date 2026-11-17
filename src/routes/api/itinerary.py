import logging
import uuid
from datetime import UTC, datetime, time

from flask import Blueprint, g, jsonify, request
from flask.typing import ResponseReturnValue
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from src.extensions.database import FareSnapshot, Itinerary, db
from src.services.fli_search import FlightQuery, filters_for_itinerary, scrape_prices
from src.services.fx_rates import get_configured_base_currency
from src.utils.filters import parse_bool

logger = logging.getLogger(__name__)

itineraries_bp = Blueprint('itineraries', __name__, url_prefix='/itineraries')

# The page routes own deadlines and the per-leg flag; this API only flips isolated state.
_TOGGLE_FIELDS = frozenset({'is_active', 'archived'})


@itineraries_bp.route('/<itinerary_id>', methods=['PATCH'])
def update_flight(itinerary_id: str) -> ResponseReturnValue:
    try:
        entry = db.session.execute(
            select(Itinerary).where(Itinerary.id == itinerary_id)
        ).scalar_one_or_none()

        if not entry:
            logger.debug('itinerary not found for update: id=%s', itinerary_id)
            return jsonify({'message': 'Entry not found', 'data': None}), 404

        data = request.get_json(silent=True) or request.form.to_dict()

        if unsupported := sorted(set(data) - _TOGGLE_FIELDS):
            logger.info(
                'rejected itinerary update: id=%s fields=%s',
                itinerary_id,
                ','.join(unsupported),
            )
            return jsonify(
                {'message': f'Unsupported field: {", ".join(unsupported)}', 'data': None}
            ), 400

        if 'is_active' in data:
            entry.is_active = parse_bool(data['is_active'], 'is_active')
            logger.info('updated itinerary: id=%s is_active=%s', itinerary_id, entry.is_active)

        if 'archived' in data:
            archived = parse_bool(data['archived'], 'archived')
            if archived:
                if entry.archived_at is None:
                    entry.archived_at = datetime.now(UTC)
            else:
                entry.archived_at = None
            logger.info('updated itinerary: id=%s archived=%s', itinerary_id, archived)

        db.session.commit()
        return jsonify({'message': 'Entry updated', 'data': entry.id})
    except ValueError as exc:
        db.session.rollback()
        logger.info('invalid itinerary toggle: id=%s error=%s', itinerary_id, exc)
        return jsonify({'message': str(exc), 'data': None}), 400
    except Exception as exc:
        db.session.rollback()
        logger.exception('update itinerary failed: id=%s', itinerary_id)
        return jsonify({'message': str(exc), 'data': None}), 400


@itineraries_bp.route('/<itinerary_id>/scrape', methods=['POST'])
def scrape_flight(itinerary_id: str) -> ResponseReturnValue:
    try:
        itinerary = db.session.execute(
            select(Itinerary)
            .options(selectinload(Itinerary.flights))
            .where(Itinerary.id == itinerary_id)
        ).scalar_one_or_none()

        if not itinerary:
            logger.debug('itinerary not found for scraping: id=%s', itinerary_id)
            return jsonify({'message': 'Entry not found', 'data': None}), 404

        today_local = datetime.now(g.tz).date()

        for flight in itinerary.flights:
            db.session.execute(
                delete(FareSnapshot)
                .where(FareSnapshot.flight_id == flight.id)
                .where(
                    FareSnapshot.created_at
                    >= datetime.combine(today_local, time.min, tzinfo=g.tz).astimezone(UTC)
                )
                .where(
                    FareSnapshot.created_at
                    <= datetime.combine(today_local, time.max, tzinfo=g.tz).astimezone(UTC)
                )
            )

        any_scraped_or_attempted = False
        if active_flights := [f for f in itinerary.flights if f.flight_date >= today_local]:
            any_scraped_or_attempted = True
            logger.info('scrape itinerary: id=%s flights=%d', itinerary_id, len(active_flights))

            base_currency = get_configured_base_currency()
            results = scrape_prices(
                [FlightQuery(f.origin, f.destination, f.flight_date) for f in active_flights],
                currency_code=base_currency,
                filters=filters_for_itinerary(itinerary),
            )

            for flight, res in zip(active_flights, results, strict=False):
                if not res.success:
                    db.session.add(
                        FareSnapshot(
                            id=str(uuid.uuid4()),
                            flight_id=flight.id,
                            created_at=datetime.now(UTC),
                            fare=None,
                            currency=base_currency,
                            scrape_status='error',
                            error_message=res.error_message or 'Scrape failed',
                        )
                    )
                    continue
                for result in res.results:
                    db.session.add(
                        FareSnapshot(
                            id=str(uuid.uuid4()),
                            flight_id=flight.id,
                            created_at=datetime.now(UTC),
                            fare=result.fare,
                            currency=result.currency,
                            flight_number=result.flight_number,
                            departure_at=result.departure_at,
                            arrival_at=result.arrival_at,
                            scrape_status='success',
                        )
                    )

        if not any_scraped_or_attempted:
            db.session.rollback()
            logger.info('scrape skipped: itinerary_id=%s reason=no_active_flights', itinerary_id)
            return jsonify(
                {'message': 'Cannot scrape: flight date has passed for all legs', 'data': None}
            ), 400

        db.session.commit()
        logger.info('scrape completed: itinerary_id=%s', itinerary_id)
        return jsonify({'message': 'Scrape completed', 'data': itinerary.id})
    except Exception as exc:
        db.session.rollback()
        logger.exception('scrape itinerary failed: id=%s', itinerary_id)
        return jsonify({'message': str(exc), 'data': None}), 400
