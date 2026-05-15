import uuid
from datetime import UTC, date, datetime

from flask import Blueprint, jsonify, request
from sqlalchemy import select

from src.database import Flight, FlightFareSnapshot, SessionLocal
from src.services.scraper import scrape_prices

flights_bp = Blueprint('flights', __name__, url_prefix='/flights')


@flights_bp.route('', methods=['POST'])
def create_flight():
    db = SessionLocal()
    try:
        data = request.get_json(silent=True) or request.form.to_dict()

        deadline_str = data.get('deadline')
        deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date() if deadline_str else None

        entry = Flight(
            id=str(uuid.uuid4()),
            origin=data.get('origin').upper(),
            destination=data.get('destination').upper(),
            flight_date=datetime.strptime(data.get('flight_date'), '%Y-%m-%d').date(),
            deadline=deadline,
            is_active=True,
        )

        db.add(entry)
        db.commit()
        return jsonify({'success': True, 'message': 'Entry created', 'data': entry})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        db.close()


@flights_bp.route('/<flight_id>', methods=['GET'])
def get_flight(flight_id):
    db = SessionLocal()
    try:
        entry = db.execute(select(Flight).where(Flight.id == flight_id)).scalar_one_or_none()

        if not entry:
            return jsonify({'success': False, 'message': 'Entry not found'}), 404

        return jsonify({'success': True, 'message': 'Entry retrieved', 'data': entry})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        db.close()


@flights_bp.route('/<flight_id>', methods=['PATCH'])
def update_flight(flight_id):
    db = SessionLocal()
    try:
        entry = db.execute(select(Flight).where(Flight.id == flight_id)).scalar_one_or_none()

        if not entry:
            return jsonify({'success': False, 'message': 'Entry not found'}), 404

        data = request.get_json(silent=True) or request.form.to_dict()

        if 'is_active' in data:
            entry.is_active = data['is_active']

        if 'notification_enabled' in data:
            entry.notification_enabled = data['notification_enabled']

        db.commit()
        return jsonify({'success': True, 'message': 'Entry updated', 'data': entry})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        db.close()


@flights_bp.route('/<flight_id>', methods=['DELETE'])
def delete_flight(flight_id):
    db = SessionLocal()
    try:
        entry = db.execute(select(Flight).where(Flight.id == flight_id)).scalar_one_or_none()

        if not entry:
            return jsonify({'success': False, 'message': 'Entry not found'}), 404

        db.delete(entry)
        db.commit()
        return jsonify({'success': True, 'message': 'Entry deleted', 'data': None})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        db.close()


@flights_bp.route('/<flight_id>/scrape', methods=['POST'])
def scrape_flight(flight_id):
    db = SessionLocal()
    try:
        entry = db.execute(select(Flight).where(Flight.id == flight_id)).scalar_one_or_none()

        if not entry:
            return jsonify({'success': False, 'message': 'Entry not found'}), 404

        if entry.flight_date < date.today():
            return jsonify(
                {'success': False, 'message': 'Cannot scrape: flight date has passed'}
            ), 400

        results = scrape_prices(
            origin=entry.origin,
            destination=entry.destination,
            flight_date=entry.flight_date,
        )

        for result in results.results:
            db.add(
                FlightFareSnapshot(
                    flight_id=flight_id,
                    created_at=datetime.now(UTC),
                    fare=result.fare,
                    flight_number=result.flight_number,
                    departure_at=result.departure_at,
                    arrival_at=result.arrival_at,
                    scrape_status='success' if results.success else 'error',
                    error_message=results.error_message,
                )
            )
            db.commit()

        return jsonify({'success': True, 'message': 'Scrape completed', 'data': entry})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        db.close()
