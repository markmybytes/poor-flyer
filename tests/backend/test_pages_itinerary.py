from datetime import UTC, date, datetime
from unittest.mock import patch

from src.extensions.database import FareSnapshot, Flight, Itinerary, db
from src.routes.pages.itinerary import _serialize_itinerary

INERTIA_HEADERS = {'X-Inertia': 'true', 'X-Inertia-Version': ''}

_MOCK_RATES = {
    'base': 'HKD',
    'rates': {'HKD': 1.0, 'USD': 0.1282},
    'last_updated': '2024-06-15T00:00:00Z',
}


def _seed_itinerary(origin='HKG', destination='NRT', with_fare=False):
    it = Itinerary(
        trip_type='SINGLE',
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db.session.add(it)
    db.session.flush()
    fl = Flight(
        itinerary_id=it.id,
        sequence=0,
        origin=origin,
        destination=destination,
        flight_date=date(2025, 12, 1),
    )
    db.session.add(fl)
    db.session.flush()
    if with_fare:
        db.session.add(
            FareSnapshot(
                flight_id=fl.id,
                fare=1200.0,
                currency='HKD',
                scrape_status='success',
                created_at=datetime.now(UTC),
            )
        )
    db.session.commit()
    return it


def test_serialize_itinerary_with_explicit_today_date(app):
    with app.app_context():
        it = _seed_itinerary(with_fare=True)
        result = _serialize_itinerary(it, 'HKD', today=date(2024, 6, 15))
        assert result['id'] == it.id
        assert result['trip_type'] == 'SINGLE'


def test_itinerary_index_renders_correct_component(client, app):
    with app.app_context():
        with patch('src.routes.pages.itinerary.get_configured_base_currency', return_value='HKD'):
            with patch('src.routes.pages.itinerary.convert_amount', side_effect=lambda a, s, t: a):
                resp = client.get('/itineraries/', headers=INERTIA_HEADERS)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['component'] == 'Itineraries/Index'


def test_itinerary_index_props_contain_itineraries_key(client, app):
    with app.app_context():
        with patch('src.routes.pages.itinerary.get_configured_base_currency', return_value='HKD'):
            with patch('src.routes.pages.itinerary.convert_amount', side_effect=lambda a, s, t: a):
                resp = client.get('/itineraries/', headers=INERTIA_HEADERS)
    data = resp.get_json()
    assert 'itineraries' in data['props']
    assert 'baseCurrency' in data['props']


def test_itinerary_index_empty_list_when_no_records(client, app):
    with app.app_context():
        with patch('src.routes.pages.itinerary.get_configured_base_currency', return_value='HKD'):
            resp = client.get('/itineraries/', headers=INERTIA_HEADERS)
    assert resp.get_json()['props']['itineraries'] == []


def test_itinerary_index_returns_seeded_itinerary(client, app):
    with app.app_context():
        _seed_itinerary()
        with patch('src.routes.pages.itinerary.get_configured_base_currency', return_value='HKD'):
            with patch('src.routes.pages.itinerary.convert_amount', side_effect=lambda a, s, t: a):
                resp = client.get('/itineraries/', headers=INERTIA_HEADERS)
    data = resp.get_json()
    assert len(data['props']['itineraries']) == 1
    assert data['props']['itineraries'][0]['tripType'] == 'SINGLE'


def test_itinerary_create_renders_correct_component(client, app):
    with app.app_context():
        resp = client.get('/itineraries/create', headers=INERTIA_HEADERS)
    assert resp.status_code == 200
    assert resp.get_json()['component'] == 'Itineraries/Create'


def test_itinerary_show_renders_detail_component(client, app):
    with app.app_context():
        it = _seed_itinerary(with_fare=True)
        iid = it.id
        with patch('src.routes.pages.itinerary.get_configured_base_currency', return_value='HKD'):
            with patch('src.routes.pages.itinerary.convert_amount', side_effect=lambda a, s, t: a):
                resp = client.get(f'/itineraries/{iid}', headers=INERTIA_HEADERS)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['component'] == 'Itineraries/Detail'
    assert data['props']['itinerary']['id'] == iid


def test_itinerary_show_not_found_redirects(client, app):
    with app.app_context():
        resp = client.get('/itineraries/nonexistent-id', headers=INERTIA_HEADERS)
    assert resp.status_code in (302, 301)
    assert '/itineraries/' in resp.headers.get('Location', '')


def test_itinerary_show_props_include_base_currency(client, app):
    with app.app_context():
        it = _seed_itinerary()
        iid = it.id
        with patch('src.routes.pages.itinerary.get_configured_base_currency', return_value='USD'):
            with patch('src.routes.pages.itinerary.convert_amount', side_effect=lambda a, s, t: a):
                resp = client.get(f'/itineraries/{iid}', headers=INERTIA_HEADERS)
    data = resp.get_json()
    assert data['props']['baseCurrency'] == 'USD'


def test_itinerary_show_serializes_statistics_as_none_without_fares(client, app):
    with app.app_context():
        it = _seed_itinerary(with_fare=False)
        iid = it.id
        with patch('src.routes.pages.itinerary.get_configured_base_currency', return_value='HKD'):
            resp = client.get(f'/itineraries/{iid}', headers=INERTIA_HEADERS)
    data = resp.get_json()
    assert data['props']['itinerary']['statistics'] is None
