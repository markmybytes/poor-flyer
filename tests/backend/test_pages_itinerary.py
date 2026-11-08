import json
from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch

from src.extensions.database import FareSnapshot, Flight, Itinerary, db
from src.routes.pages.itinerary import _serialize_itinerary

INERTIA_HEADERS = {'X-Inertia': 'true', 'X-Inertia-Version': ''}

_MOCK_RATES = {
    'base': 'HKD',
    'rates': {'HKD': 1.0, 'USD': 0.1282},
    'last_updated': '2024-06-15T00:00:00Z',
}


def _seed_itinerary(
    origin='HKG', destination='NRT', with_fare=False, archived=False, deadline=None
):
    it = Itinerary(
        trip_type='SINGLE',
        is_active=True,
        created_at=datetime.now(UTC),
        archived_at=datetime.now(UTC) if archived else None,
        deadline=deadline,
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


def test_itinerary_index_excludes_archived_by_default(client, app):
    with app.app_context():
        _seed_itinerary()
        _seed_itinerary(archived=True)
        with patch('src.routes.pages.itinerary.get_configured_base_currency', return_value='HKD'):
            resp = client.get('/itineraries/', headers=INERTIA_HEADERS)
    itineraries = resp.get_json()['props']['itineraries']
    assert len(itineraries) == 1
    assert itineraries[0]['archivedAt'] is None


def test_itinerary_index_archived_filter_returns_only_archived(client, app):
    with app.app_context():
        _seed_itinerary()
        _seed_itinerary(archived=True)
        with patch('src.routes.pages.itinerary.get_configured_base_currency', return_value='HKD'):
            resp = client.get('/itineraries/?archived=1', headers=INERTIA_HEADERS)
    itineraries = resp.get_json()['props']['itineraries']
    assert len(itineraries) == 1
    assert itineraries[0]['archivedAt'] is not None


def test_serialize_itinerary_skips_rule37_when_disabled(app):
    with app.app_context():
        it = _seed_itinerary(with_fare=True, deadline=date.today() + timedelta(days=60))
        with patch('src.routes.pages.itinerary.convert_amount', side_effect=lambda a, s, t: a):
            result = _serialize_itinerary(it, 'HKD', today=date.today(), include_rule37=False)
    assert result['rule37_analysis'] is None
    assert result['statistics'] is not None


def test_itinerary_index_default_view_includes_rule37_analysis(client, app):
    with app.app_context():
        _seed_itinerary(with_fare=True, deadline=date.today() + timedelta(days=60))
        with patch('src.routes.pages.itinerary.get_configured_base_currency', return_value='HKD'):
            with patch('src.routes.pages.itinerary.convert_amount', side_effect=lambda a, s, t: a):
                resp = client.get('/itineraries/', headers=INERTIA_HEADERS)
    itineraries = resp.get_json()['props']['itineraries']
    assert itineraries[0]['rule37Analysis'] is not None


def test_itinerary_index_archived_view_skips_rule37_analysis(client, app):
    with app.app_context():
        _seed_itinerary(with_fare=True, archived=True, deadline=date.today() + timedelta(days=60))
        with patch('src.routes.pages.itinerary.get_configured_base_currency', return_value='HKD'):
            with patch('src.routes.pages.itinerary.convert_amount', side_effect=lambda a, s, t: a):
                resp = client.get('/itineraries/?archived=1', headers=INERTIA_HEADERS)
    itineraries = resp.get_json()['props']['itineraries']
    assert itineraries[0]['rule37Analysis'] is None
    assert itineraries[0]['statistics'] is not None


def test_itinerary_create_renders_correct_component(client, app):
    with app.app_context():
        resp = client.get('/itineraries/create', headers=INERTIA_HEADERS)
    assert resp.status_code == 200
    assert resp.get_json()['component'] == 'Itineraries/Create'


def test_itinerary_create_submit_persists_and_redirects(client, app):
    resp = client.post(
        '/itineraries',
        data=json.dumps(
            {
                'trip_type': 'ROUND_TRIP',
                'cabin_class': 'business',
                'max_stops': 'NON_STOP',
                'airlines': ['cx', 'jl'],
                'flights': [
                    {'origin': 'hkg', 'destination': 'nrt', 'flight_date': '2025-12-01'},
                    {'origin': 'nrt', 'destination': 'hkg', 'flight_date': '2025-12-08'},
                ],
            }
        ),
        content_type='application/json',
    )

    assert resp.status_code == 302
    assert resp.headers['Location'] == '/'
    with app.app_context():
        itinerary = db.session.query(Itinerary).one()
        assert itinerary.trip_type == 'ROUND_TRIP'
        assert itinerary.cabin_class == 'BUSINESS'
        assert itinerary.max_stops == 'NON_STOP'
        assert itinerary.airlines == ['CX', 'JL']
        flights = (
            db.session.query(Flight)
            .filter_by(itinerary_id=itinerary.id)
            .order_by(Flight.sequence)
            .all()
        )
        assert [(f.origin, f.destination) for f in flights] == [
            ('HKG', 'NRT'),
            ('NRT', 'HKG'),
        ]


def test_itinerary_create_submit_honors_is_active(client, app):
    payload = {
        'trip_type': 'SINGLE',
        'flights': [{'origin': 'HKG', 'destination': 'NRT', 'flight_date': '2025-12-01'}],
    }
    resp = client.post(
        '/itineraries',
        data=json.dumps({**payload, 'is_active': False}),
        content_type='application/json',
    )
    assert resp.status_code == 302
    with app.app_context():
        assert db.session.query(Itinerary).one().is_active is False

    resp = client.post('/itineraries', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 302
    with app.app_context():
        assert db.session.query(Itinerary).all()[-1].is_active is True


def test_itinerary_create_submit_invalid_payload_returns_422(client, app):
    resp = client.post(
        '/itineraries',
        data=json.dumps(
            {
                'trip_type': 'SINGLE',
                'cabin_class': 'SUITE',
                'flights': [{'origin': 'HKG', 'destination': 'NRT', 'flight_date': '2025-12-01'}],
            }
        ),
        content_type='application/json',
        headers=INERTIA_HEADERS,
    )

    assert resp.status_code == 422
    data = resp.get_json()
    assert data['component'] == 'Itineraries/Create'
    assert data['props']['errors']['itinerary'] == '請檢查輸入內容'
    with app.app_context():
        assert db.session.query(Itinerary).count() == 0


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
