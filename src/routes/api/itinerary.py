import logging
import uuid
from datetime import UTC, datetime, time

from flask import Blueprint, g, jsonify, request
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from src.extensions.database import FareSnapshot, Flight, Itinerary, db
from src.services.fli_search import FlightQuery, filters_for_itinerary, scrape_prices
from src.services.fx_rates import FXRatesError, convert_amount, get_configured_base_currency
from src.services.itinerary import create_itinerary

logger = logging.getLogger(__name__)

itineraries_bp = Blueprint('itineraries', __name__, url_prefix='/itineraries')


@itineraries_bp.route('', methods=['POST'])
def create_flight():
    try:
        data = request.get_json(silent=True) or request.form.to_dict()
        itinerary = create_itinerary(data)

        db.session.commit()
        logger.info(
            'Created itinerary: id=%s flights=%d', itinerary.id, len(data.get('flights', []))
        )
        return jsonify({'success': True, 'message': 'Entry created', 'data': itinerary.id})
    except Exception as e:
        db.session.rollback()
        logger.exception('Error creating itinerary')
        return jsonify({'success': False, 'message': str(e)}), 400


@itineraries_bp.route('/<itinerary_id>', methods=['GET'])
def get_flight(itinerary_id):
    try:
        base_currency = get_configured_base_currency()
        entry = db.session.execute(
            select(Itinerary)
            .options(selectinload(Itinerary.flights).selectinload(Flight.fare_snapshots))
            .where(Itinerary.id == itinerary_id)
        ).scalar_one_or_none()

        if not entry:
            logger.debug('Itinerary not found: id=%s', itinerary_id)
            return jsonify({'success': False, 'message': 'Entry not found'}), 404

        latest_success: FareSnapshot | None = None
        for flight in entry.flights:
            for snapshot in flight.fare_snapshots:
                if snapshot.scrape_status != 'success' or snapshot.fare is None:
                    continue
                if latest_success is None or snapshot.created_at > latest_success.created_at:
                    latest_success = snapshot

        converted_preview = None
        if latest_success is not None:
            src_currency = (latest_success.currency or base_currency).strip().upper()
            converted_value = float(latest_success.fare)
            try:
                converted_value = convert_amount(converted_value, src_currency, base_currency)
            except FXRatesError:
                logger.warning('Failed to convert fare: itinerary_id=%s', itinerary_id)
                pass

            converted_preview = {
                'amount': converted_value,
                'currency': base_currency,
                'source_currency': src_currency,
                'created_at': latest_success.created_at,
            }

        return jsonify(
            {
                'success': True,
                'message': 'Entry retrieved',
                'data': {
                    'id': entry.id,
                    'base_currency': base_currency,
                    'latest_converted_fare': converted_preview,
                },
            }
        )
    except Exception as e:
        db.session.rollback()
        logger.exception('Error retrieving itinerary: id=%s', itinerary_id)
        return jsonify({'success': False, 'message': str(e)}), 400


@itineraries_bp.route('/<itinerary_id>', methods=['PATCH'])
def update_flight(itinerary_id):
    try:
        entry = db.session.execute(
            select(Itinerary).where(Itinerary.id == itinerary_id)
        ).scalar_one_or_none()

        if not entry:
            logger.debug('Itinerary not found for update: %s', itinerary_id)
            return jsonify({'success': False, 'message': 'Entry not found'}), 404

        data = request.get_json(silent=True) or request.form.to_dict()

        if {'cabin_class', 'max_stops', 'airlines'} & data.keys():
            return jsonify({'message': '搜尋條件於建立後不可修改', 'data': None}), 400

        if 'is_active' in data:
            entry.is_active = data['is_active']
            logger.info('Updated itinerary: id=%s is_active=%s', itinerary_id, data['is_active'])

        if 'deadline' in data:
            deadline_str = data['deadline']
            if deadline_str:
                entry.deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
            else:
                entry.deadline = None
            logger.info('Updated itinerary: id=%s deadline=%s', itinerary_id, entry.deadline)

        db.session.commit()
        return jsonify({'success': True, 'message': 'Entry updated', 'data': entry.id})
    except Exception as e:
        db.session.rollback()
        logger.exception('Error updating itinerary: id=%s', itinerary_id)
        return jsonify({'success': False, 'message': str(e)}), 400


@itineraries_bp.route('/<itinerary_id>', methods=['DELETE'])
def delete_flight(itinerary_id):
    try:
        entry = db.session.execute(
            select(Itinerary).where(Itinerary.id == itinerary_id)
        ).scalar_one_or_none()

        if not entry:
            logger.debug('Itinerary not found for deletion: %s', itinerary_id)
            return jsonify({'success': False, 'message': 'Entry not found'}), 404

        db.session.delete(entry)
        db.session.commit()
        logger.info('Deleted itinerary: id=%s', itinerary_id)
        return jsonify({'success': True, 'message': 'Entry deleted', 'data': None})
    except Exception as e:
        db.session.rollback()
        logger.exception('Error deleting itinerary: id=%s', itinerary_id)
        return jsonify({'success': False, 'message': str(e)}), 400


@itineraries_bp.route('/<itinerary_id>/scrape', methods=['POST'])
def scrape_flight(itinerary_id):
    try:
        itinerary = db.session.execute(
            select(Itinerary)
            .options(selectinload(Itinerary.flights))
            .where(Itinerary.id == itinerary_id)
        ).scalar_one_or_none()

        if not itinerary:
            logger.debug('Itinerary not found for scraping: %s', itinerary_id)
            return jsonify({'success': False, 'message': 'Entry not found'}), 404

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
            logger.info('Scraping %d flights for itinerary %s', len(active_flights), itinerary_id)

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
            logger.warning('No active flights to scrape: itinerary_id=%s', itinerary_id)
            return jsonify(
                {'success': False, 'message': 'Cannot scrape: flight date has passed for all legs'}
            ), 400

        db.session.commit()
        logger.info('Scrape completed: itinerary_id=%s', itinerary_id)
        return jsonify({'success': True, 'message': 'Scrape completed', 'data': itinerary.id})
    except Exception as e:
        db.session.rollback()
        logger.exception('Error scraping itinerary: id=%s', itinerary_id)
        return jsonify({'success': False, 'message': str(e)}), 400
