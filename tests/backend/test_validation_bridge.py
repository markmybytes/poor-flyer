"""Bridge transport tests: one ValidationError handler, two response shapes."""

import json
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from src.extensions.database import Itinerary, db

INERTIA_HEADERS = {'X-Inertia': 'true', 'X-Inertia-Version': ''}

_MOCK_RATES = {
    'base': 'HKD',
    'rates': {'HKD': 1.0, 'USD': 0.1282},
    'last_updated': '2024-06-15T00:00:00Z',
}


def _seed_itinerary(app) -> str:
    with app.app_context():
        itinerary = Itinerary(trip_type='SINGLE', is_active=True, created_at=datetime.now(UTC))
        db.session.add(itinerary)
        db.session.commit()
        return itinerary.id


def test_page_error_lands_in_the_session_bag_as_plain_strings(client, app):
    resp = client.post(
        '/settings',
        data=json.dumps({'currency': {'cache_ttl': 'abc'}}),
        content_type='application/json',
        headers=INERTIA_HEADERS,
    )

    assert resp.status_code == 302
    assert resp.headers['Location'] == '/settings/'
    with patch('src.routes.pages.settings.get_rates', return_value=_MOCK_RATES):
        props = client.get('/settings/', headers=INERTIA_HEADERS).get_json()['props']
    assert props['errors'] == {'settings': 'Cache TTL must be an integer greater than 0'}
    assert isinstance(props['errors']['settings'], str)


def test_page_error_redirects_to_the_same_origin_referrer(client, app):
    iid = _seed_itinerary(app)

    resp = client.patch(
        f'/itineraries/{iid}/status',
        data={'is_active': 'maybe'},
        headers={**INERTIA_HEADERS, 'Referer': 'http://localhost/itineraries/?archived=1'},
    )

    assert resp.status_code == 303
    assert resp.headers['Location'].endswith('/itineraries/?archived=1')


def test_api_error_uses_the_422_envelope_with_string_arrays(client):
    resp = client.post(
        '/api/settings/fx-rates/refresh',
        data=json.dumps({'base_currency': ['USD']}),
        content_type='application/json',
    )

    assert resp.status_code == 422
    body = resp.get_json()
    assert body['message'] == 'Validation failed'
    assert body['data'] is None
    # the bridge emits snake keys; the provider camelizes them exactly once
    assert set(body['errors']) == {'baseCurrency'}
    assert isinstance(body['errors']['baseCurrency'], list)
    assert all(isinstance(message, str) for message in body['errors']['baseCurrency'])


def test_api_passes_validation_through_to_the_service(client):
    with patch('src.routes.api.settings.get_rates', return_value=_MOCK_RATES):
        resp = client.post(
            '/api/settings/fx-rates/refresh',
            data=json.dumps({'base_currency': 'usd'}),
            content_type='application/json',
        )

    assert resp.status_code == 200
    assert resp.get_json()['data']['baseCurrency'] == 'HKD'


@pytest.mark.parametrize(
    'referer',
    ['http://localhost//evil.example', 'http://localhost/\\evil.example'],
)
def test_referrer_that_browsers_normalize_off_origin_falls_back(client, app, referer):
    iid = _seed_itinerary(app)

    resp = client.patch(
        f'/itineraries/{iid}/status',
        data={'is_active': 'maybe'},
        headers={**INERTIA_HEADERS, 'Referer': referer},
    )

    assert resp.status_code == 303
    assert resp.headers['Location'].endswith(f'/itineraries/{iid}')


@pytest.mark.parametrize(
    'payload',
    [
        {
            'trip_type': 'SINGLE',
            'flights': [{'origin': 'HK', 'destination': 'NRT', 'flight_date': '2026-12-01'}],
        },
        {
            'trip_type': 'BIZARRE',
            'flights': [{'origin': 'HKG', 'destination': 'NRT', 'flight_date': '2026-12-01'}],
        },
    ],
)
def test_create_schema_errors_collapse_to_the_itinerary_bag(client, app, payload):
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
    props = client.get('/itineraries/create', headers=INERTIA_HEADERS).get_json()['props']
    assert props['errors'] == {'itinerary': '請檢查輸入內容'}


def test_create_with_a_camel_case_key_is_rejected(client, app):
    resp = client.post(
        '/itineraries',
        data=json.dumps(
            {
                'trip_type': 'SINGLE',
                'notifyPerLeg': True,
                'flights': [{'origin': 'HKG', 'destination': 'NRT', 'flight_date': '2026-12-01'}],
            }
        ),
        content_type='application/json',
        headers=INERTIA_HEADERS,
    )

    assert resp.status_code == 302
    assert resp.headers['Location'] == '/itineraries/create'
    with app.app_context():
        assert db.session.query(Itinerary).count() == 0
    props = client.get('/itineraries/create', headers=INERTIA_HEADERS).get_json()['props']
    assert props['errors'] == {'itinerary': '請檢查輸入內容'}


def test_patch_with_a_camel_case_key_is_rejected(client, app):
    iid = _seed_itinerary(app)

    resp = client.patch(
        f'/itineraries/{iid}',
        data=json.dumps({'notifyPerLeg': True}),
        content_type='application/json',
        headers=INERTIA_HEADERS,
    )

    assert resp.status_code == 303
    with app.app_context():
        entry = db.session.get(Itinerary, iid)
        assert entry.notify_per_leg is False
    props = client.get(f'/itineraries/{iid}', headers=INERTIA_HEADERS).get_json()['props']
    assert set(props['errors']) == {'notifyPerLeg'}


def test_status_explicit_null_is_rejected(client, app):
    iid = _seed_itinerary(app)

    resp = client.patch(
        f'/itineraries/{iid}/status',
        data=json.dumps({'is_active': None}),
        content_type='application/json',
        headers=INERTIA_HEADERS,
    )

    assert resp.status_code == 303
    with app.app_context():
        assert db.session.get(Itinerary, iid).is_active is True
    props = client.get(f'/itineraries/{iid}', headers=INERTIA_HEADERS).get_json()['props']
    assert props['errors'] == {'status': 'Invalid is_active'}
