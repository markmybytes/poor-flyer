from unittest.mock import patch

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
