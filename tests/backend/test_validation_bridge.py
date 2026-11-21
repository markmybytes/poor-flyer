"""Bridge transport tests: one ValidationError handler, two response shapes."""

import json
import logging
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from flask import g, session
from pydantic import ValidationError

from src.extensions.database import Itinerary, db
from src.schemas.itinerary import ItineraryCreate
from src.services.errors import FieldIssue, InvalidFieldsError
from src.validation import handle_invalid_fields, handle_validation_error

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
    assert props['errors'] == {'currency.cacheTtl': '快取有效時間必須是大於 0 的整數'}
    assert isinstance(props['errors']['currency.cacheTtl'], str)


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
    assert body['message'] == '驗證失敗'
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


def test_api_error_keeps_dotted_keys_and_camelizes_each_snake_key(app):
    """A nested payload yields dotted keys; the provider camelizes each snake segment once."""
    with pytest.raises(ValidationError) as excinfo:
        ItineraryCreate.model_validate(
            {
                'flights': [
                    {'origin': 'HK', 'destination': 'NRT', 'flight_date': '2026-12-01'},
                    {'origin': 'HKG', 'destination': 'NRT', 'flight_date': '2026-12-32'},
                ],
                'notify_per_leg': 'maybe',
            }
        )

    with app.test_request_context('/api/settings/fx-rates/refresh', method='POST'):
        response, status = handle_validation_error(excinfo.value)
        body = response.get_json()

    assert status == 422
    assert body['message'] == '驗證失敗'
    assert body['data'] is None
    assert set(body['errors']) == {'flights.0.origin', 'flights.1.flightDate', 'notifyPerLeg'}
    assert body['errors']['flights.0.origin'] == ['IATA 代碼無效']
    assert body['errors']['flights.1.flightDate'] == ['航班日期無效']
    assert body['errors']['notifyPerLeg'] == ['格式不正確']


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
    ('payload', 'field'),
    [
        (
            {
                'trip_type': 'SINGLE',
                'flights': [{'origin': 'HK', 'destination': 'NRT', 'flight_date': '2026-12-01'}],
            },
            'flights.0.origin',
        ),
        (
            {
                'trip_type': 'BIZARRE',
                'flights': [{'origin': 'HKG', 'destination': 'NRT', 'flight_date': '2026-12-01'}],
            },
            'tripType',
        ),
    ],
)
def test_create_schema_errors_keep_their_own_field_key(client, app, payload, field):
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
    assert set(props['errors']) == {field}
    assert isinstance(props['errors'][field], str)


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
    assert set(props['errors']) == {'notifyPerLeg'}
    assert isinstance(props['errors']['notifyPerLeg'], str)


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
    assert props['errors'] == {'isActive': '追蹤狀態無效'}


def test_domain_failure_on_a_page_lands_in_the_bag_and_redirects_to_the_fallback(app):
    with app.test_request_context('/itineraries', method='POST'):
        g.validation_redirect = '/itineraries/create'
        response = handle_invalid_fields(
            InvalidFieldsError([FieldIssue('flights.0.origin', 'IATA 代碼無效')])
        )
        bag = dict(session['errors'])

    assert response.status_code == 302
    assert response.headers['Location'] == '/itineraries/create'
    assert bag == {'flights.0.origin': 'IATA 代碼無效'}


def test_domain_failure_on_an_api_request_uses_the_422_envelope(app):
    with app.test_request_context('/api/settings/fx-rates/refresh', method='POST'):
        response, status = handle_invalid_fields(
            InvalidFieldsError(
                [
                    FieldIssue('currency.base_currency', '不支援的基準貨幣'),
                    FieldIssue('currency.cache_ttl', '快取有效時間必須是大於 0 的整數'),
                ]
            )
        )
        body = response.get_json()

    assert status == 422
    assert body['message'] == '驗證失敗'
    assert body['data'] is None
    # snake keys here; the provider camelizes them exactly once
    assert body['errors'] == {
        'currency.baseCurrency': ['不支援的基準貨幣'],
        'currency.cacheTtl': ['快取有效時間必須是大於 0 的整數'],
    }


def test_domain_failure_logs_once_at_the_boundary(app, caplog):
    error = InvalidFieldsError(
        [
            FieldIssue('currency.base_currency', '不支援的基準貨幣'),
            FieldIssue('currency.cache_ttl', '格式不正確'),
        ]
    )

    with (
        app.test_request_context('/settings', method='POST'),
        caplog.at_level(logging.INFO, logger='src.validation'),
    ):
        handle_invalid_fields(error)

    records = [record for record in caplog.records if record.name == 'src.validation']
    assert len(records) == 1
    assert records[0].levelno == logging.INFO
    assert records[0].getMessage() == (
        'rejected page payload: fields=currency.base_currency,currency.cache_ttl'
    )
