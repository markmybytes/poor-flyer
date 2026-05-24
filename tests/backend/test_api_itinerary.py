import json
import uuid
from datetime import UTC, date, datetime
from unittest.mock import patch

from src.extensions.database import FareSnapshot, Flight, Itinerary, db

_MOCK_RATES = {
    'base': 'HKD',
    'rates': {'HKD': 1.0, 'USD': 0.1282, 'JPY': 19.23},
    'last_updated': '2024-06-15T00:00:00Z',
}


def _make_itinerary(trip_type='SINGLE', deadline=None):
    it = Itinerary(
        trip_type=trip_type,
        deadline=deadline,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db.session.add(it)
    db.session.flush()
    return it


def _make_flight(itinerary_id, origin='HKG', destination='NRT', sequence=0):
    f = Flight(
        itinerary_id=itinerary_id,
        sequence=sequence,
        origin=origin,
        destination=destination,
        flight_date=date(2025, 12, 1),
    )
    db.session.add(f)
    db.session.flush()
    return f


def _make_snapshot(flight_id, fare=1200.0, status='success', currency='HKD'):
    s = FareSnapshot(
        flight_id=flight_id,
        fare=fare,
        currency=currency,
        scrape_status=status,
        created_at=datetime.now(UTC),
    )
    db.session.add(s)
    db.session.flush()
    return s


def test_create_itinerary_single_flight(client, app):
    with app.app_context():
        with patch('src.routes.api.itinerary.get_configured_base_currency', return_value='HKD'):
            resp = client.post(
                '/api/itineraries',
                data=json.dumps(
                    {
                        'trip_type': 'SINGLE',
                        'flights': [
                            {'origin': 'HKG', 'destination': 'NRT', 'flight_date': '2025-12-01'}
                        ],
                    }
                ),
                content_type='application/json',
            )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert isinstance(data['data'], str)


def test_create_itinerary_with_deadline(client, app):
    with app.app_context():
        resp = client.post(
            '/api/itineraries',
            data=json.dumps(
                {
                    'trip_type': 'SINGLE',
                    'deadline': '2025-11-01',
                    'flights': [
                        {'origin': 'HKG', 'destination': 'LHR', 'flight_date': '2025-12-15'}
                    ],
                }
            ),
            content_type='application/json',
        )
    assert resp.status_code == 200
    assert resp.get_json()['success'] is True


def test_create_itinerary_invalid_date_returns_400(client, app):
    with app.app_context():
        resp = client.post(
            '/api/itineraries',
            data=json.dumps(
                {
                    'trip_type': 'SINGLE',
                    'flights': [
                        {'origin': 'HKG', 'destination': 'NRT', 'flight_date': 'not-a-date'}
                    ],
                }
            ),
            content_type='application/json',
        )
    assert resp.status_code == 400
    assert resp.get_json()['success'] is False


def test_get_itinerary_not_found(client, app):
    with app.app_context():
        with patch('src.routes.api.itinerary.get_configured_base_currency', return_value='HKD'):
            resp = client.get(f'/api/itineraries/{uuid.uuid4()}')
    assert resp.status_code == 404
    assert resp.get_json()['success'] is False


def test_get_itinerary_success_no_fare(client, app):
    with app.app_context():
        it = _make_itinerary()
        _make_flight(it.id)
        db.session.commit()
        iid = it.id

        with patch('src.routes.api.itinerary.get_configured_base_currency', return_value='HKD'):
            with patch('src.routes.api.itinerary.convert_amount', side_effect=Exception('skip')):
                resp = client.get(f'/api/itineraries/{iid}')

    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert data['data']['id'] == iid
    assert data['data']['latestConvertedFare'] is None


def test_get_itinerary_with_fare_conversion(client, app):
    with app.app_context():
        it = _make_itinerary()
        fl = _make_flight(it.id)
        _make_snapshot(fl.id, fare=1200.0, currency='HKD')
        db.session.commit()
        iid = it.id

        with patch('src.routes.api.itinerary.get_configured_base_currency', return_value='HKD'):
            with patch('src.routes.api.itinerary.convert_amount', return_value=1200.0):
                resp = client.get(f'/api/itineraries/{iid}')

    assert resp.status_code == 200
    data = resp.get_json()
    assert data['data']['latestConvertedFare']['amount'] == 1200.0


def test_patch_itinerary_deadline(client, app):
    with app.app_context():
        it = _make_itinerary()
        db.session.commit()
        iid = it.id

    resp = client.patch(
        f'/api/itineraries/{iid}',
        data=json.dumps({'deadline': '2025-10-01'}),
        content_type='application/json',
    )
    assert resp.status_code == 200
    assert resp.get_json()['success'] is True


def test_patch_itinerary_not_found(client, app):
    with app.app_context():
        resp = client.patch(
            f'/api/itineraries/{uuid.uuid4()}',
            data=json.dumps({'is_active': False}),
            content_type='application/json',
        )
    assert resp.status_code == 404
    assert resp.get_json()['success'] is False


def test_delete_itinerary(client, app):
    with app.app_context():
        it = _make_itinerary()
        db.session.commit()
        iid = it.id

    resp = client.delete(f'/api/itineraries/{iid}')
    assert resp.status_code == 200
    assert resp.get_json()['success'] is True


def test_delete_itinerary_not_found(client, app):
    with app.app_context():
        resp = client.delete(f'/api/itineraries/{uuid.uuid4()}')
    assert resp.status_code == 404


def test_create_itinerary_origins_uppercased(client, app):
    with app.app_context():
        resp = client.post(
            '/api/itineraries',
            data=json.dumps(
                {
                    'trip_type': 'SINGLE',
                    'flights': [
                        {'origin': 'hkg', 'destination': 'nrt', 'flight_date': '2025-12-01'}
                    ],
                }
            ),
            content_type='application/json',
        )
    assert resp.status_code == 200
    with app.app_context():
        it_id = resp.get_json()['data']
        flight = db.session.query(Flight).filter_by(itinerary_id=it_id).first()
        assert flight.origin == 'HKG'
        assert flight.destination == 'NRT'
