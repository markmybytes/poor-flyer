import uuid
from datetime import UTC, date, datetime

from flask import Blueprint, jsonify, request
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from src.extensions.database import FareSnapshot, Flight, Itinerary, db
from src.services.scraper import FlightQuery, scrape_prices

flights_bp = Blueprint('flights', __name__, url_prefix='/flights')


@flights_bp.route('', methods=['POST'])
def create_flight():
    session = db.session
    try:
        data = request.get_json(silent=True) or request.form.to_dict()

        deadline_str = data.get('deadline')
        deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date() if deadline_str else None

        itinerary = Itinerary(
            id=str(uuid.uuid4()),
            trip_type=data.get('trip_type', 'SINGLE'),
            deadline=deadline,
            is_active=True,
            created_at=datetime.now(UTC),
        )

        session.add(itinerary)

        flights_data = data.get('flights', [])
        for i, flight_data in enumerate(flights_data):
            flight = Flight(
                id=str(uuid.uuid4()),
                itinerary_id=itinerary.id,
                sequence=i,
                origin=flight_data.get('origin', '').upper(),
                destination=flight_data.get('destination', '').upper(),
                flight_date=datetime.strptime(flight_data.get('flight_date'), '%Y-%m-%d').date(),
            )
            session.add(flight)

        session.commit()
        return jsonify({'success': True, 'message': 'Entry created', 'data': itinerary.id})
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400


@flights_bp.route('/<flight_id>', methods=['GET'])
def get_flight(flight_id):
    try:
        entry = db.session.execute(
            select(Itinerary)
            .options(selectinload(Itinerary.flights))
            .where(Itinerary.id == flight_id)
        ).scalar_one_or_none()

        if not entry:
            return jsonify({'success': False, 'message': 'Entry not found'}), 404

        return jsonify({'success': True, 'message': 'Entry retrieved', 'data': entry.id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@flights_bp.route('/<flight_id>', methods=['PATCH'])
def update_flight(flight_id):
    session = db.session
    try:
        entry = session.execute(
            select(Itinerary).where(Itinerary.id == flight_id)
        ).scalar_one_or_none()

        if not entry:
            return jsonify({'success': False, 'message': 'Entry not found'}), 404

        data = request.get_json(silent=True) or request.form.to_dict()

        if 'is_active' in data:
            entry.is_active = data['is_active']

        session.commit()
        return jsonify({'success': True, 'message': 'Entry updated', 'data': entry.id})
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400


@flights_bp.route('/<flight_id>', methods=['DELETE'])
def delete_flight(flight_id):
    session = db.session
    try:
        entry = session.execute(
            select(Itinerary).where(Itinerary.id == flight_id)
        ).scalar_one_or_none()

        if not entry:
            return jsonify({'success': False, 'message': 'Entry not found'}), 404

        session.delete(entry)
        session.commit()
        return jsonify({'success': True, 'message': 'Entry deleted', 'data': None})
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400


@flights_bp.route('/<flight_id>/scrape', methods=['POST'])
def scrape_flight(flight_id):
    session = db.session
    try:
        itinerary = session.execute(
            select(Itinerary)
            .options(selectinload(Itinerary.flights))
            .where(Itinerary.id == flight_id)
        ).scalar_one_or_none()

        if not itinerary:
            return jsonify({'success': False, 'message': 'Entry not found'}), 404

        today = date.today()
        today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=UTC)
        today_end = datetime.combine(today, datetime.max.time()).replace(tzinfo=UTC)

        for flight in itinerary.flights:
            session.execute(
                delete(FareSnapshot)
                .where(FareSnapshot.flight_id == flight.id)
                .where(FareSnapshot.created_at >= today_start)
                .where(FareSnapshot.created_at <= today_end)
            )

        any_scraped_or_attempted = False
        if active_flights := [f for f in itinerary.flights if f.flight_date >= today]:
            any_scraped_or_attempted = True

            results = scrape_prices(
                [FlightQuery(f.origin, f.destination, f.flight_date) for f in active_flights]
            )

            for flight, res in zip(active_flights, results, strict=False):
                for result in res.results:
                    session.add(
                        FareSnapshot(
                            id=str(uuid.uuid4()),
                            flight_id=flight.id,
                            created_at=datetime.now(UTC),
                            fare=result.fare,
                            currency=result.currency,
                            flight_number=result.flight_number,
                            departure_at=result.departure_at,
                            arrival_at=result.arrival_at,
                            scrape_status='success' if res.success else 'error',
                            error_message=res.error_message,
                        )
                    )

        if not any_scraped_or_attempted:
            session.rollback()
            return jsonify(
                {'success': False, 'message': 'Cannot scrape: flight date has passed for all legs'}
            ), 400

        session.commit()
        return jsonify({'success': True, 'message': 'Scrape completed', 'data': itinerary.id})
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
