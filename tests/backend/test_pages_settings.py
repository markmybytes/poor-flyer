import json
from unittest.mock import patch

import pytest

from src.services import setting
from src.services.errors import FieldIssue, InvalidFieldsError

INERTIA_HEADERS = {'X-Inertia': 'true', 'X-Inertia-Version': ''}

_MOCK_RATES = {
    'base': 'HKD',
    'rates': {'HKD': 1.0, 'USD': 0.1282},
    'last_updated': '2024-06-15T00:00:00Z',
}


def test_settings_index_renders_correct_component(client, app):
    with app.app_context():
        with patch('src.routes.pages.settings.get_rates', return_value=_MOCK_RATES):
            with patch('src.routes.pages.settings.setting.get_all_masked', return_value={}):
                resp = client.get('/settings/', headers=INERTIA_HEADERS)
    assert resp.status_code == 200
    assert resp.get_json()['component'] == 'Settings/Index'


def test_settings_index_props_contain_required_keys(client, app):
    with app.app_context():
        with patch('src.routes.pages.settings.get_rates', return_value=_MOCK_RATES):
            with patch('src.routes.pages.settings.setting.get_all_masked', return_value={}):
                resp = client.get('/settings/', headers=INERTIA_HEADERS)
    props = resp.get_json()['props']
    assert 'settings' in props
    assert 'supportedCurrencies' in props
    assert 'fxStatus' in props


def test_settings_index_supported_currencies_is_list(client, app):
    with app.app_context():
        with patch('src.routes.pages.settings.get_rates', return_value=_MOCK_RATES):
            with patch('src.routes.pages.settings.setting.get_all_masked', return_value={}):
                resp = client.get('/settings/', headers=INERTIA_HEADERS)
    props = resp.get_json()['props']
    assert isinstance(props['supportedCurrencies'], list)
    assert 'HKD' in props['supportedCurrencies']


def test_settings_index_fx_error_sets_error_prop(client, app):
    from src.services.fx_rates import FXRatesError

    with app.app_context():
        with patch(
            'src.routes.pages.settings.get_rates',
            side_effect=FXRatesError('API unavailable'),
        ):
            with patch('src.routes.pages.settings.setting.get_all_masked', return_value={}):
                resp = client.get('/settings/', headers=INERTIA_HEADERS)
    assert resp.status_code == 200
    props = resp.get_json()['props']
    assert props['fxStatus']['error'] == 'API unavailable'
    assert props['fxStatus']['rates'] == {}


def test_settings_index_fx_status_base_currency_matches_config(client, app):
    with app.app_context():
        with patch('src.routes.pages.settings.get_rates', return_value=_MOCK_RATES):
            with patch('src.routes.pages.settings.setting.get_all_masked', return_value={}):
                with patch(
                    'src.routes.pages.settings.get_configured_base_currency', return_value='USD'
                ):
                    resp = client.get('/settings/', headers=INERTIA_HEADERS)
    props = resp.get_json()['props']
    assert props['fxStatus']['baseCurrency'] in ('HKD', 'USD')


def test_settings_index_settings_props_contain_currency_section(client, app):
    with app.app_context():
        with patch('src.routes.pages.settings.get_rates', return_value=_MOCK_RATES):
            with patch(
                'src.routes.pages.settings.setting.get_all_masked',
                return_value={'base_currency': 'JPY'},
            ):
                resp = client.get('/settings/', headers=INERTIA_HEADERS)
    props = resp.get_json()['props']
    assert 'currency' in props['settings']
    assert 'smtp' in props['settings']


def test_settings_save_updates_and_redirects(client, app):
    resp = client.post(
        '/settings',
        data=json.dumps({'currency': {'base_currency': 'usd'}}),
        content_type='application/json',
    )

    assert resp.status_code == 302
    assert resp.headers['Location'] == '/settings/'
    with app.app_context():
        assert setting.get('currency', 'base_currency') == 'USD'


def test_settings_save_untouched_password_is_not_clobbered(client, app):
    # oracle gate-7 fix: masked '***' from get_all_masked must never replace a stored password
    with app.app_context():
        setting.set_many('smtp', {'password': 'real-secret'})

    with patch('src.routes.pages.settings.get_rates', return_value=_MOCK_RATES):
        resp = client.post(
            '/settings',
            data=json.dumps({'smtp': {'host': 'smtp.example.com'}}),
            content_type='application/json',
        )

    assert resp.status_code == 302
    with app.app_context():
        assert setting.get('smtp', 'password') == 'real-secret'


def test_settings_save_retyped_password_overwrites(client, app):
    with app.app_context():
        setting.set_many('smtp', {'password': 'real-secret'})

    with patch('src.routes.pages.settings.get_rates', return_value=_MOCK_RATES):
        resp = client.post(
            '/settings',
            data=json.dumps({'smtp': {'password': 'new-secret'}}),
            content_type='application/json',
        )

    assert resp.status_code == 302
    with app.app_context():
        assert setting.get('smtp', 'password') == 'new-secret'


def test_settings_save_flashes_success_notice(client, app):
    resp = client.post(
        '/settings',
        data=json.dumps({'currency': {'base_currency': 'usd'}}),
        content_type='application/json',
        headers=INERTIA_HEADERS,
    )

    assert resp.status_code == 302
    with patch('src.routes.pages.settings.get_rates', return_value=_MOCK_RATES):
        props = client.get('/settings/', headers=INERTIA_HEADERS).get_json()['props']
    assert props['flash'] == {'success': '設定已儲存'}
    assert props['errors'] == {}


def test_settings_index_props_flags_and_numbers_are_typed(client, app):
    with app.app_context():
        setting.set_many('currency', {'cache_ttl': '120'})
        setting.set_many('itinerary', {'disable_departured_itineraries': 'true'})
        setting.set_many('smtp', {'port': '587', 'require_auth': 'true'})

        with patch('src.routes.pages.settings.get_rates', return_value=_MOCK_RATES):
            props = client.get('/settings/', headers=INERTIA_HEADERS).get_json()['props']

    settings = props['settings']
    assert settings['currency']['cacheTtl'] == 120
    assert settings['itinerary']['disableDeparturedItineraries'] is True
    assert settings['smtp']['port'] == 587
    assert settings['smtp']['requireAuth'] is True


def test_settings_index_still_reads_legacy_store_tokens(client, app):
    # store-side normalization keeps rows written before the schema took over
    with app.app_context():
        setting.set_many('itinerary', {'disable_departured_itineraries': 'yes'})
        setting.set_many('smtp', {'require_auth': 'on'})

        with patch('src.routes.pages.settings.get_rates', return_value=_MOCK_RATES):
            props = client.get('/settings/', headers=INERTIA_HEADERS).get_json()['props']

    assert props['settings']['itinerary']['disableDeparturedItineraries'] is True
    assert props['settings']['smtp']['requireAuth'] is True


def test_settings_index_retired_enable_tokens_read_false(client, app):
    with app.app_context():
        setting.set_many('itinerary', {'disable_departured_itineraries': 'enable'})
        setting.set_many('smtp', {'require_auth': 'enabled'})

        with patch('src.routes.pages.settings.get_rates', return_value=_MOCK_RATES):
            props = client.get('/settings/', headers=INERTIA_HEADERS).get_json()['props']

    assert props['settings']['itinerary']['disableDeparturedItineraries'] is False
    assert props['settings']['smtp']['requireAuth'] is False


def test_settings_save_accepts_boolean_flags(client, app):
    resp = client.post(
        '/settings',
        data=json.dumps(
            {
                'itinerary': {'disable_departured_itineraries': False},
                'smtp': {'require_auth': False},
            }
        ),
        content_type='application/json',
    )

    assert resp.status_code == 302
    with app.app_context():
        assert setting.get('itinerary', 'disable_departured_itineraries') == 'false'
        assert setting.get('smtp', 'require_auth') == 'false'


@pytest.mark.parametrize(
    ('token', 'stored'),
    [
        ('true', 'true'),
        ('TRUE', 'true'),
        ('1', 'true'),
        ('yes', 'true'),
        ('y', 'true'),
        ('t', 'true'),
        ('on', 'true'),
        ('false', 'false'),
        ('0', 'false'),
        ('no', 'false'),
        ('n', 'false'),
        ('f', 'false'),
        ('off', 'false'),
    ],
)
def test_settings_save_accepts_native_flag_tokens(client, app, token, stored):
    resp = client.post(
        '/settings',
        data=json.dumps({'itinerary': {'disable_departured_itineraries': token}}),
        content_type='application/json',
    )

    assert resp.status_code == 302
    with app.app_context():
        assert setting.get('itinerary', 'disable_departured_itineraries') == stored


@pytest.mark.parametrize(
    ('section', 'field', 'token', 'bag_key'),
    [
        (
            'itinerary',
            'disable_departured_itineraries',
            'enable',
            'itinerary.disableDeparturedItineraries',
        ),
        (
            'itinerary',
            'disable_departured_itineraries',
            None,
            'itinerary.disableDeparturedItineraries',
        ),
        ('smtp', 'require_auth', 'enabled', 'smtp.requireAuth'),
        ('smtp', 'require_auth', None, 'smtp.requireAuth'),
    ],
)
def test_settings_save_rejects_store_tokens_and_explicit_null(
    client, app, section, field, token, bag_key
):
    with patch('src.routes.pages.settings.get_rates', return_value=_MOCK_RATES):
        resp = client.post(
            '/settings',
            data=json.dumps({section: {field: token}}),
            content_type='application/json',
            headers=INERTIA_HEADERS,
        )

    assert resp.status_code == 302
    assert resp.headers['Location'] == '/settings/'
    with patch('src.routes.pages.settings.get_rates', return_value=_MOCK_RATES):
        props = client.get('/settings/', headers=INERTIA_HEADERS).get_json()['props']
    assert props['errors'] == {bag_key: '格式不正確'}


def test_settings_save_invalid_currency_redirects_with_errors(client, app):
    with patch('src.routes.pages.settings.get_rates', return_value=_MOCK_RATES):
        resp = client.post(
            '/settings',
            data=json.dumps({'currency': {'base_currency': 'XXX'}}),
            content_type='application/json',
            headers=INERTIA_HEADERS,
        )

    assert resp.status_code == 302
    assert resp.headers['Location'] == '/settings/'

    with patch('src.routes.pages.settings.get_rates', return_value=_MOCK_RATES):
        data = client.get('/settings/', headers=INERTIA_HEADERS).get_json()
    assert data['component'] == 'Settings/Index'
    assert data['props']['errors'] == {'currency.baseCurrency': '不支援的基準貨幣'}


def test_settings_service_errors_map_every_field_at_once(client, app, mocker):
    mocker.patch(
        'src.routes.pages.settings.setting.update',
        side_effect=InvalidFieldsError(
            [
                FieldIssue('currency.base_currency', '不支援的基準貨幣'),
                FieldIssue('currency.cache_ttl', '快取有效時間必須是大於 0 的整數'),
            ]
        ),
    )

    resp = client.post(
        '/settings',
        data=json.dumps({'currency': {'base_currency': 'XXX'}}),
        content_type='application/json',
        headers=INERTIA_HEADERS,
    )

    assert resp.status_code == 302
    with patch('src.routes.pages.settings.get_rates', return_value=_MOCK_RATES):
        props = client.get('/settings/', headers=INERTIA_HEADERS).get_json()['props']
    assert props['errors'] == {
        'currency.baseCurrency': '不支援的基準貨幣',
        'currency.cacheTtl': '快取有效時間必須是大於 0 的整數',
    }


@pytest.mark.parametrize(
    ('field', 'message', 'bag_key'),
    [
        ('currency.cache_ttl', '快取有效時間必須是大於 0 的整數', 'currency.cacheTtl'),
        ('smtp.port', 'SMTP 連接埠必須是整數', 'smtp.port'),
    ],
)
def test_settings_service_error_maps_to_its_field(client, app, mocker, field, message, bag_key):
    mocker.patch(
        'src.routes.pages.settings.setting.update',
        side_effect=InvalidFieldsError([FieldIssue(field=field, message=message)]),
    )

    resp = client.post(
        '/settings',
        data=json.dumps({'smtp': {'port': '587'}}),
        content_type='application/json',
        headers=INERTIA_HEADERS,
    )

    assert resp.status_code == 302
    assert resp.headers['Location'] == '/settings/'
    with patch('src.routes.pages.settings.get_rates', return_value=_MOCK_RATES):
        props = client.get('/settings/', headers=INERTIA_HEADERS).get_json()['props']
    assert props['errors'] == {bag_key: message}
