import json
from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch

import pytest
from fli.models.airline import AIRLINE_NAMES

from src.extensions.database import FareSnapshot, Flight, Itinerary, db
from src.routes.pages.itinerary import _serialize_itinerary

INERTIA_HEADERS = {'X-Inertia': 'true', 'X-Inertia-Version': ''}

_MOCK_RATES = {
    'base': 'HKD',
    'rates': {'HKD': 1.0, 'USD': 0.1282},
    'last_updated': '2024-06-15T00:00:00Z',
}


def _seed_itinerary(
    origin='HKG',
    destination='NRT',
    with_fare=False,
    archived=False,
    deadline=None,
    flight_date=date(2025, 12, 1),
    notify_per_leg=False,
):
    it = Itinerary(
        trip_type='SINGLE',
        is_active=True,
        notify_per_leg=notify_per_leg,
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
        flight_date=flight_date,
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
        assert result['notify_per_leg'] is False


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
    assert data['props']['itineraries'][0]['notifyPerLeg'] is False


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


def test_itinerary_create_props_include_airlines(client, app):
    with app.app_context():
        resp = client.get('/itineraries/create', headers=INERTIA_HEADERS)
    airlines = resp.get_json()['props']['airlines']
    codes = [airline['code'] for airline in airlines]

    assert set(airlines[0]) == {'code', 'name'}
    assert len(airlines) == len(AIRLINE_NAMES)
    assert codes == sorted(codes)
    assert {'code': 'CX', 'name': 'Cathay Pacific'} in airlines
    assert '7C' in codes
    assert '_7C' not in codes


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

    assert resp.status_code in (302, 303)
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
    assert resp.status_code in (302, 303)
    with app.app_context():
        assert db.session.query(Itinerary).one().is_active is False

    resp = client.post('/itineraries', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code in (302, 303)
    with app.app_context():
        assert db.session.query(Itinerary).all()[-1].is_active is True


def test_itinerary_create_submit_honors_notify_per_leg(client, app):
    payload = {
        'trip_type': 'SINGLE',
        'flights': [{'origin': 'HKG', 'destination': 'NRT', 'flight_date': '2025-12-01'}],
    }
    resp = client.post('/itineraries', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code in (302, 303)
    with app.app_context():
        assert db.session.query(Itinerary).one().notify_per_leg is False

    resp = client.post(
        '/itineraries',
        data=json.dumps({**payload, 'notify_per_leg': True}),
        content_type='application/json',
    )
    assert resp.status_code in (302, 303)
    with app.app_context():
        assert db.session.query(Itinerary).all()[-1].notify_per_leg is True


def test_itinerary_create_submit_invalid_payload_redirects_with_errors(client, app):
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

    assert resp.status_code == 302
    assert resp.headers['Location'] == '/itineraries/create'
    with app.app_context():
        assert db.session.query(Itinerary).count() == 0

    data = client.get('/itineraries/create', headers=INERTIA_HEADERS).get_json()
    assert data['component'] == 'Itineraries/Create'
    assert data['props']['errors']['itinerary'] == '請檢查輸入內容'
    assert 'airlines' in data['props']


def test_itinerary_create_submit_past_deadline_redirects_with_errors(client, app):
    resp = client.post(
        '/itineraries',
        data=json.dumps(
            {
                'trip_type': 'SINGLE',
                'deadline': (date.today() - timedelta(days=1)).isoformat(),
                'flights': [{'origin': 'HKG', 'destination': 'NRT', 'flight_date': '2025-12-01'}],
            }
        ),
        content_type='application/json',
        headers=INERTIA_HEADERS,
    )

    assert resp.status_code == 302
    assert resp.headers['Location'] == '/itineraries/create'
    with app.app_context():
        assert db.session.query(Itinerary).count() == 0

    data = client.get('/itineraries/create', headers=INERTIA_HEADERS).get_json()
    assert data['props']['errors'] == {'itinerary': '請檢查輸入內容'}


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
    assert data['props']['itinerary']['notifyPerLeg'] is False


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


def _future_departure():
    return date.today() + timedelta(days=30)


def test_itinerary_update_deadline_persists_and_redirects(client, app):
    departure = _future_departure()
    with app.app_context():
        it = _seed_itinerary(flight_date=departure)
        iid = it.id

    resp = client.patch(
        f'/itineraries/{iid}',
        data=json.dumps({'deadline': (departure - timedelta(days=5)).isoformat()}),
        content_type='application/json',
        headers=INERTIA_HEADERS,
    )

    assert resp.status_code in (302, 303)
    assert resp.headers['Location'].endswith(f'/itineraries/{iid}')
    with app.app_context():
        assert db.session.get(Itinerary, iid).deadline == departure - timedelta(days=5)


def test_itinerary_update_empty_deadline_clears(client, app):
    with app.app_context():
        it = _seed_itinerary(deadline=_future_departure())
        iid = it.id

    resp = client.patch(
        f'/itineraries/{iid}',
        data=json.dumps({'deadline': ''}),
        content_type='application/json',
        headers=INERTIA_HEADERS,
    )

    assert resp.status_code in (302, 303)
    with app.app_context():
        assert db.session.get(Itinerary, iid).deadline is None


def test_itinerary_update_empty_payload_changes_nothing(client, app):
    deadline = _future_departure()
    with app.app_context():
        it = _seed_itinerary(deadline=deadline, notify_per_leg=True)
        iid = it.id

    resp = client.patch(
        f'/itineraries/{iid}',
        data=json.dumps({}),
        content_type='application/json',
        headers=INERTIA_HEADERS,
    )

    assert resp.status_code in (302, 303)
    with app.app_context():
        entry = db.session.get(Itinerary, iid)
        assert entry.deadline == deadline
        assert entry.notify_per_leg is True
    props = client.get(f'/itineraries/{iid}', headers=INERTIA_HEADERS).get_json()['props']
    assert props['errors'] == {}


def test_itinerary_update_absent_deadline_is_unchanged(client, app):
    deadline = _future_departure()
    with app.app_context():
        it = _seed_itinerary(deadline=deadline)
        iid = it.id

    resp = client.patch(
        f'/itineraries/{iid}',
        data=json.dumps({'notify_per_leg': True}),
        content_type='application/json',
        headers=INERTIA_HEADERS,
    )

    assert resp.status_code in (302, 303)
    with app.app_context():
        entry = db.session.get(Itinerary, iid)
        assert entry.deadline == deadline
        assert entry.notify_per_leg is True


def test_itinerary_update_absent_notify_per_leg_is_unchanged(client, app):
    with app.app_context():
        it = _seed_itinerary(flight_date=_future_departure(), notify_per_leg=True)
        iid = it.id

    resp = client.patch(
        f'/itineraries/{iid}',
        data=json.dumps({'deadline': _future_departure().isoformat()}),
        content_type='application/json',
        headers=INERTIA_HEADERS,
    )

    assert resp.status_code in (302, 303)
    with app.app_context():
        assert db.session.get(Itinerary, iid).notify_per_leg is True


def test_itinerary_update_past_deadline_redirects_with_detail_props(client, app):
    with app.app_context():
        it = _seed_itinerary(flight_date=_future_departure())
        iid = it.id

    resp = client.patch(
        f'/itineraries/{iid}',
        data=json.dumps({'deadline': (date.today() - timedelta(days=1)).isoformat()}),
        content_type='application/json',
        headers=INERTIA_HEADERS,
    )

    assert resp.status_code == 303
    assert resp.headers['Location'].endswith(f'/itineraries/{iid}')
    data = client.get(f'/itineraries/{iid}', headers=INERTIA_HEADERS).get_json()
    assert data['component'] == 'Itineraries/Detail'
    assert data['props']['errors'] == {'deadline': 'Deadline must not be in the past'}
    assert data['props']['itinerary']['id'] == iid
    assert 'baseCurrency' in data['props']
    with app.app_context():
        assert db.session.get(Itinerary, iid).deadline is None


def test_itinerary_update_deadline_after_departure_redirects_with_errors(client, app):
    departure = _future_departure()
    with app.app_context():
        it = _seed_itinerary(flight_date=departure)
        iid = it.id

    resp = client.patch(
        f'/itineraries/{iid}',
        data=json.dumps({'deadline': (departure + timedelta(days=1)).isoformat()}),
        content_type='application/json',
        headers=INERTIA_HEADERS,
    )

    assert resp.status_code == 303
    data = client.get(f'/itineraries/{iid}', headers=INERTIA_HEADERS).get_json()
    assert data['props']['errors'] == {'deadline': 'Deadline must not be after the first departure'}


@pytest.mark.parametrize('offset', [0, 30])
def test_itinerary_update_accepts_inclusive_deadline_bounds(client, app, offset):
    departure = _future_departure()
    with app.app_context():
        it = _seed_itinerary(flight_date=departure)
        iid = it.id

    resp = client.patch(
        f'/itineraries/{iid}',
        data=json.dumps({'deadline': (date.today() + timedelta(days=offset)).isoformat()}),
        content_type='application/json',
        headers=INERTIA_HEADERS,
    )

    assert resp.status_code in (302, 303)
    with app.app_context():
        assert db.session.get(Itinerary, iid).deadline == date.today() + timedelta(days=offset)


def test_itinerary_update_invalid_deadline_format_redirects_with_errors(client, app):
    with app.app_context():
        it = _seed_itinerary(flight_date=_future_departure())
        iid = it.id

    resp = client.patch(
        f'/itineraries/{iid}',
        data=json.dumps({'deadline': '2026-13-45'}),
        content_type='application/json',
        headers=INERTIA_HEADERS,
    )

    assert resp.status_code == 303
    data = client.get(f'/itineraries/{iid}', headers=INERTIA_HEADERS).get_json()
    assert data['props']['errors'] == {'deadline': 'Deadline must be a valid date'}


@pytest.mark.parametrize(
    ('token', 'stored'),
    [
        (True, True),
        ('true', True),
        ('1', True),
        (False, False),
        ('false', False),
        ('0', False),
    ],
)
def test_itinerary_update_notify_per_leg_tokens(client, app, token, stored):
    with app.app_context():
        it = _seed_itinerary()
        iid = it.id

    resp = client.patch(
        f'/itineraries/{iid}',
        data=json.dumps({'notify_per_leg': token}),
        content_type='application/json',
        headers=INERTIA_HEADERS,
    )

    assert resp.status_code in (302, 303)
    with app.app_context():
        assert db.session.get(Itinerary, iid).notify_per_leg is stored


@pytest.mark.parametrize('token', ['maybe', 'none', ''])
def test_itinerary_update_invalid_notify_per_leg_redirects_with_errors(client, app, token):
    with app.app_context():
        it = _seed_itinerary(notify_per_leg=True)
        iid = it.id

    resp = client.patch(
        f'/itineraries/{iid}',
        data=json.dumps({'notify_per_leg': token}),
        content_type='application/json',
        headers=INERTIA_HEADERS,
    )

    assert resp.status_code == 303
    data = client.get(f'/itineraries/{iid}', headers=INERTIA_HEADERS).get_json()
    assert data['props']['errors'] == {'notifyPerLeg': 'Invalid notify_per_leg'}
    with app.app_context():
        assert db.session.get(Itinerary, iid).notify_per_leg is True


def test_itinerary_create_submit_flashes_success_notice(client, app):
    resp = client.post(
        '/itineraries',
        data=json.dumps(
            {
                'trip_type': 'SINGLE',
                'flights': [{'origin': 'HKG', 'destination': 'NRT', 'flight_date': '2025-12-01'}],
            }
        ),
        content_type='application/json',
        headers=INERTIA_HEADERS,
    )

    assert resp.status_code == 302
    assert resp.headers['Location'] == '/'
    # '/' redirects again; follow both hops so the flash lands where the browser renders
    target = client.get('/', headers=INERTIA_HEADERS).headers['Location']
    props = client.get(target, headers=INERTIA_HEADERS).get_json()['props']
    assert props['flash'] == {'success': '已成功建立票價追蹤'}
    assert props['errors'] == {}


def test_itinerary_update_flashes_success_notice(client, app):
    with app.app_context():
        it = _seed_itinerary(flight_date=_future_departure())
        iid = it.id

    resp = client.patch(
        f'/itineraries/{iid}',
        data=json.dumps({'notify_per_leg': True}),
        content_type='application/json',
        headers=INERTIA_HEADERS,
    )

    assert resp.status_code == 303
    props = client.get(f'/itineraries/{iid}', headers=INERTIA_HEADERS).get_json()['props']
    assert props['flash'] == {'success': '已更新設定'}
    assert props['errors'] == {}


def test_page_errors_are_consumed_on_first_render(client, app):
    with app.app_context():
        it = _seed_itinerary(flight_date=_future_departure())
        iid = it.id

    client.patch(
        f'/itineraries/{iid}',
        data=json.dumps({'deadline': '2026-13-45'}),
        content_type='application/json',
        headers=INERTIA_HEADERS,
    )

    first = client.get(f'/itineraries/{iid}', headers=INERTIA_HEADERS).get_json()
    second = client.get(f'/itineraries/{iid}', headers=INERTIA_HEADERS).get_json()

    assert first['props']['errors'] == {'deadline': 'Deadline must be a valid date'}
    assert second['props']['errors'] == {}


def test_page_flash_is_consumed_on_first_render(client, app):
    with app.app_context():
        it = _seed_itinerary(flight_date=_future_departure())
        iid = it.id

    client.patch(
        f'/itineraries/{iid}',
        data=json.dumps({'notify_per_leg': True}),
        content_type='application/json',
        headers=INERTIA_HEADERS,
    )

    first = client.get(f'/itineraries/{iid}', headers=INERTIA_HEADERS).get_json()
    second = client.get(f'/itineraries/{iid}', headers=INERTIA_HEADERS).get_json()

    assert first['props']['flash'] == {'success': '已更新設定'}
    assert second['props']['flash'] == {}


def test_itinerary_update_not_found_redirects(client, app):
    resp = client.patch(
        '/itineraries/nonexistent-id',
        data=json.dumps({'deadline': ''}),
        content_type='application/json',
        headers=INERTIA_HEADERS,
    )

    assert resp.status_code in (302, 303)
    assert '/itineraries/' in resp.headers['Location']


def test_itinerary_delete_removes_record_and_redirects(client, app):
    with app.app_context():
        it = _seed_itinerary()
        iid = it.id

    resp = client.delete(f'/itineraries/{iid}', headers=INERTIA_HEADERS)

    assert resp.status_code in (302, 303)
    assert '/itineraries/' in resp.headers['Location']
    with app.app_context():
        assert db.session.get(Itinerary, iid) is None


def test_itinerary_delete_not_found_redirects(client, app):
    resp = client.delete('/itineraries/nonexistent-id', headers=INERTIA_HEADERS)

    assert resp.status_code in (302, 303)
    assert '/itineraries/' in resp.headers['Location']


@pytest.mark.parametrize(('token', 'stored'), [('false', False), ('true', True)])
def test_itinerary_create_submit_reads_is_active_tokens(client, app, token, stored):
    resp = client.post(
        '/itineraries',
        data=json.dumps(
            {
                'trip_type': 'SINGLE',
                'is_active': token,
                'flights': [{'origin': 'HKG', 'destination': 'NRT', 'flight_date': '2025-12-01'}],
            }
        ),
        content_type='application/json',
    )

    assert resp.status_code in (302, 303)
    with app.app_context():
        assert db.session.query(Itinerary).one().is_active is stored


@pytest.mark.parametrize(
    'payload',
    [
        {'trip_type': 'SINGLE'},
        {'trip_type': 'SINGLE', 'flights': []},
    ],
)
def test_itinerary_create_submit_requires_a_flight(client, app, payload):
    resp = client.post(
        '/itineraries',
        data=json.dumps(payload),
        content_type='application/json',
        headers=INERTIA_HEADERS,
    )

    assert resp.status_code == 302
    assert resp.headers['Location'] == '/itineraries/create'
    with app.app_context():
        assert db.session.query(Itinerary).count() == 0
    data = client.get('/itineraries/create', headers=INERTIA_HEADERS).get_json()
    assert data['props']['errors'] == {'itinerary': '請檢查輸入內容'}


def test_itinerary_create_submit_rejects_form_encoded_legs(client, app):
    # form encoding cannot express flights[]; the schema's min-1 rule rejects it
    resp = client.post(
        '/itineraries',
        data={'trip_type': 'SINGLE', 'is_active': 'true'},
        headers=INERTIA_HEADERS,
    )

    assert resp.status_code == 302
    assert resp.headers['Location'] == '/itineraries/create'
    with app.app_context():
        assert db.session.query(Itinerary).count() == 0
    data = client.get('/itineraries/create', headers=INERTIA_HEADERS).get_json()
    assert data['props']['errors'] == {'itinerary': '請檢查輸入內容'}


def test_itinerary_create_submit_invalid_notify_redirects_with_errors(client, app):
    resp = client.post(
        '/itineraries',
        data=json.dumps(
            {
                'trip_type': 'SINGLE',
                'notify_per_leg': 'maybe',
                'flights': [{'origin': 'HKG', 'destination': 'NRT', 'flight_date': '2025-12-01'}],
            }
        ),
        content_type='application/json',
        headers=INERTIA_HEADERS,
    )

    assert resp.status_code == 302
    data = client.get('/itineraries/create', headers=INERTIA_HEADERS).get_json()
    assert data['props']['errors'] == {'itinerary': '請檢查輸入內容'}
    with app.app_context():
        assert db.session.query(Itinerary).count() == 0


def test_itinerary_create_submit_deadline_after_departure_redirects_with_errors(client, app):
    departure = _future_departure()
    resp = client.post(
        '/itineraries',
        data=json.dumps(
            {
                'trip_type': 'SINGLE',
                'deadline': (departure + timedelta(days=1)).isoformat(),
                'flights': [
                    {'origin': 'HKG', 'destination': 'NRT', 'flight_date': departure.isoformat()}
                ],
            }
        ),
        content_type='application/json',
        headers=INERTIA_HEADERS,
    )

    assert resp.status_code == 302
    with app.app_context():
        assert db.session.query(Itinerary).count() == 0

    data = client.get('/itineraries/create', headers=INERTIA_HEADERS).get_json()
    assert data['props']['errors'] == {'itinerary': '請檢查輸入內容'}


@pytest.mark.parametrize('offset', [0, 30])
def test_itinerary_create_submit_accepts_inclusive_deadline_bounds(client, app, offset):
    departure = _future_departure()
    resp = client.post(
        '/itineraries',
        data=json.dumps(
            {
                'trip_type': 'SINGLE',
                'deadline': (date.today() + timedelta(days=offset)).isoformat(),
                'flights': [
                    {'origin': 'HKG', 'destination': 'NRT', 'flight_date': departure.isoformat()}
                ],
            }
        ),
        content_type='application/json',
    )

    assert resp.status_code in (302, 303)
    with app.app_context():
        assert db.session.query(Itinerary).one().deadline == date.today() + timedelta(days=offset)


def test_itinerary_create_submit_invalid_deadline_format_redirects_with_errors(client, app):
    resp = client.post(
        '/itineraries',
        data=json.dumps(
            {
                'trip_type': 'SINGLE',
                'deadline': '2026-13-45',
                'flights': [{'origin': 'HKG', 'destination': 'NRT', 'flight_date': '2025-12-01'}],
            }
        ),
        content_type='application/json',
        headers=INERTIA_HEADERS,
    )

    assert resp.status_code == 302
    with app.app_context():
        assert db.session.query(Itinerary).count() == 0

    data = client.get('/itineraries/create', headers=INERTIA_HEADERS).get_json()
    assert data['props']['errors'] == {'itinerary': '請檢查輸入內容'}


def _patch_status(client, itinerary_id, payload, **headers):
    return client.patch(
        f'/itineraries/{itinerary_id}/status',
        data=json.dumps(payload),
        content_type='application/json',
        headers={**INERTIA_HEADERS, **headers},
    )


def test_status_toggle_is_active_persists_and_redirects_to_detail(client, app):
    with app.app_context():
        it = _seed_itinerary()
        iid = it.id

    resp = _patch_status(client, iid, {'is_active': False})

    assert resp.status_code == 303
    assert resp.headers['Location'].endswith(f'/itineraries/{iid}')
    with app.app_context():
        assert db.session.get(Itinerary, iid).is_active is False


def test_status_archive_sets_timestamp_and_flashes_notice(client, app):
    with app.app_context():
        it = _seed_itinerary()
        iid = it.id

    resp = _patch_status(client, iid, {'archived': True})

    assert resp.status_code == 303
    with app.app_context():
        assert db.session.get(Itinerary, iid).archived_at is not None
    props = client.get(f'/itineraries/{iid}', headers=INERTIA_HEADERS).get_json()['props']
    assert props['flash'] == {'success': '已封存'}
    assert props['errors'] == {}


def test_status_restore_clears_timestamp_and_flashes_notice(client, app):
    with app.app_context():
        it = _seed_itinerary(archived=True)
        iid = it.id

    resp = _patch_status(client, iid, {'archived': False})

    assert resp.status_code == 303
    with app.app_context():
        assert db.session.get(Itinerary, iid).archived_at is None
    props = client.get(f'/itineraries/{iid}', headers=INERTIA_HEADERS).get_json()['props']
    assert props['flash'] == {'success': '已恢復追蹤'}


def test_status_is_active_toggle_flashes_nothing(client, app):
    with app.app_context():
        it = _seed_itinerary()
        iid = it.id

    _patch_status(client, iid, {'is_active': False})

    props = client.get(f'/itineraries/{iid}', headers=INERTIA_HEADERS).get_json()['props']
    assert props['flash'] == {}


def test_status_accepts_form_encoded_tokens(client, app):
    with app.app_context():
        it = _seed_itinerary(archived=True)
        iid = it.id

    resp = client.patch(
        f'/itineraries/{iid}/status',
        data={'archived': 'false', 'is_active': 'false'},
        headers=INERTIA_HEADERS,
    )

    assert resp.status_code in (302, 303)
    with app.app_context():
        entry = db.session.get(Itinerary, iid)
        assert entry.archived_at is None
        assert entry.is_active is False


def test_status_archive_twice_keeps_first_archived_at(client, app):
    with app.app_context():
        it = _seed_itinerary(archived=True)
        it.archived_at = datetime(2020, 1, 1, tzinfo=UTC)
        db.session.commit()
        iid = it.id

    resp = _patch_status(client, iid, {'archived': True})

    assert resp.status_code == 303
    with app.app_context():
        assert db.session.get(Itinerary, iid).archived_at.year == 2020


def test_status_unknown_itinerary_redirects_to_index(client, app):
    resp = _patch_status(client, 'nonexistent-id', {'is_active': False})

    assert resp.status_code in (302, 303)
    assert resp.headers['Location'].endswith('/itineraries/')


@pytest.mark.parametrize(
    'payload',
    [
        {'deadline': '2030-01-01'},
        {'notify_per_leg': True},
        {'cabin_class': 'FIRST'},
        {'max_stops': 'ONE_STOP'},
        {'airlines': ['JL']},
        {'unexpected': 'value'},
        {'is_active': False, 'deadline': '2030-01-01'},
    ],
)
def test_status_rejects_unsupported_fields(client, app, payload):
    with app.app_context():
        it = _seed_itinerary()
        it.cabin_class = 'BUSINESS'
        it.max_stops = 'NON_STOP'
        it.airlines = ['CX']
        it.notify_per_leg = True
        db.session.commit()
        iid = it.id

    resp = _patch_status(client, iid, payload)

    assert resp.status_code == 303
    with app.app_context():
        unchanged = db.session.get(Itinerary, iid)
        assert unchanged.is_active is True
        assert unchanged.deadline is None
        assert unchanged.notify_per_leg is True
        assert unchanged.cabin_class == 'BUSINESS'
        assert unchanged.max_stops == 'NON_STOP'
        assert unchanged.airlines == ['CX']
    props = client.get(f'/itineraries/{iid}', headers=INERTIA_HEADERS).get_json()['props']
    assert props['errors']['status'].startswith('Unsupported field: ')


@pytest.mark.parametrize(
    ('token', 'archived'),
    [(True, True), ('true', True), ('1', True), (False, False), ('false', False), ('0', False)],
)
def test_status_archived_tokens(client, app, token, archived):
    with app.app_context():
        it = _seed_itinerary(archived=not archived)
        iid = it.id

    resp = _patch_status(client, iid, {'archived': token})

    assert resp.status_code in (302, 303)
    with app.app_context():
        assert (db.session.get(Itinerary, iid).archived_at is not None) is archived


def test_status_invalid_token_reports_error_and_keeps_state(client, app):
    with app.app_context():
        it = _seed_itinerary()
        iid = it.id

    resp = _patch_status(client, iid, {'is_active': 'maybe'})

    assert resp.status_code == 303
    with app.app_context():
        assert db.session.get(Itinerary, iid).is_active is True
    props = client.get(f'/itineraries/{iid}', headers=INERTIA_HEADERS).get_json()['props']
    assert props['errors'] == {'status': 'Invalid is_active'}


def test_status_archive_keeps_existing_deadline(client, app):
    deadline = date.today() + timedelta(days=30)
    with app.app_context():
        it = _seed_itinerary(deadline=deadline)
        iid = it.id

    _patch_status(client, iid, {'archived': True})

    with app.app_context():
        entry = db.session.get(Itinerary, iid)
        assert entry.archived_at is not None
        assert entry.deadline == deadline


def test_status_redirects_to_same_origin_referrer(client, app):
    with app.app_context():
        it = _seed_itinerary(archived=True)
        iid = it.id

    resp = _patch_status(
        client, iid, {'archived': False}, Referer='http://localhost/itineraries/?archived=1'
    )

    assert resp.status_code == 303
    assert resp.headers['Location'].endswith('/itineraries/?archived=1')


def test_status_ignores_external_referrer(client, app):
    with app.app_context():
        it = _seed_itinerary()
        iid = it.id

    resp = _patch_status(
        client, iid, {'archived': True}, Referer='http://evil.example/itineraries/?archived=1'
    )

    assert resp.status_code == 303
    assert resp.headers['Location'].endswith(f'/itineraries/{iid}')


def test_status_without_toggle_keys_is_a_noop_redirect(client, app):
    with app.app_context():
        it = _seed_itinerary()
        iid = it.id

    resp = _patch_status(client, iid, {})

    assert resp.status_code in (302, 303)
    assert resp.headers['Location'].endswith(f'/itineraries/{iid}')
    with app.app_context():
        entry = db.session.get(Itinerary, iid)
        assert entry.is_active is True
        assert entry.archived_at is None
