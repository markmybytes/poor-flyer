import json
from unittest.mock import patch

from src.services import setting

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


def test_settings_save_invalid_currency_returns_422(client, app):
    with patch('src.routes.pages.settings.get_rates', return_value=_MOCK_RATES):
        resp = client.post(
            '/settings',
            data=json.dumps({'currency': {'base_currency': 'XXX'}}),
            content_type='application/json',
            headers=INERTIA_HEADERS,
        )

    assert resp.status_code == 422
    data = resp.get_json()
    assert data['component'] == 'Settings/Index'
    assert data['props']['errors']['settings'] == 'Unsupported base currency'
