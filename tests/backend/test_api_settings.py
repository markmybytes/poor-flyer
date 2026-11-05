import json
from unittest.mock import patch

_MOCK_RATES = {
    'base': 'HKD',
    'rates': {'HKD': 1.0, 'USD': 0.1282},
    'last_updated': '2024-06-15T00:00:00Z',
}


def test_get_settings_returns_structure(client, app):
    with app.app_context():
        with patch('src.routes.api.settings.setting.get_all_masked', return_value={}):
            resp = client.get('/api/settings')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert 'smtp' in data['data']
    assert 'email' in data['data']
    assert 'currency' in data['data']


def test_get_settings_currency_defaults(client, app):
    with app.app_context():
        with patch('src.routes.api.settings.setting.get_all_masked', return_value={}):
            resp = client.get('/api/settings')
    data = resp.get_json()
    assert data['data']['currency']['baseCurrency'] == 'HKD'
    assert data['data']['currency']['cacheTtl'] == '86400'


def test_patch_settings_updates_base_currency(client, app):
    with app.app_context():
        with patch('src.routes.api.settings.setting.get_all_masked', return_value={}):
            with patch('src.routes.api.settings.setting.set_many'):
                resp = client.patch(
                    '/api/settings',
                    data=json.dumps({'currency': {'base_currency': 'USD'}}),
                    content_type='application/json',
                )
    assert resp.status_code == 200
    assert resp.get_json()['success'] is True


def test_patch_settings_unsupported_currency_returns_400(client, app):
    with app.app_context():
        with patch('src.routes.api.settings.setting.get_all_masked', return_value={}):
            resp = client.patch(
                '/api/settings',
                data=json.dumps({'currency': {'base_currency': 'XXX'}}),
                content_type='application/json',
            )
    assert resp.status_code == 400
    assert resp.get_json()['success'] is False


def test_patch_settings_invalid_cache_ttl_returns_400(client, app):
    with app.app_context():
        with patch('src.routes.api.settings.setting.get_all_masked', return_value={}):
            resp = client.patch(
                '/api/settings',
                data=json.dumps({'currency': {'cache_ttl': -10}}),
                content_type='application/json',
            )
    assert resp.status_code == 400
    assert 'Cache TTL' in resp.get_json()['message']


def test_patch_settings_zero_cache_ttl_returns_400(client, app):
    with app.app_context():
        with patch('src.routes.api.settings.setting.get_all_masked', return_value={}):
            resp = client.patch(
                '/api/settings',
                data=json.dumps({'currency': {'cache_ttl': 0}}),
                content_type='application/json',
            )
    assert resp.status_code == 400


def test_patch_settings_updates_email_recipients(client, app):
    with app.app_context():
        with patch('src.routes.api.settings.setting.get_all_masked', return_value={}):
            with patch('src.routes.api.settings.setting.set_many'):
                resp = client.patch(
                    '/api/settings',
                    data=json.dumps({'email': {'recipients': 'a@b.com,c@d.com'}}),
                    content_type='application/json',
                )
    assert resp.status_code == 200
    assert resp.get_json()['success'] is True


def test_patch_settings_invalid_smtp_port_returns_400(client, app):
    with app.app_context():
        with patch('src.routes.api.settings.setting.get_all_masked', return_value={}):
            resp = client.patch(
                '/api/settings',
                data=json.dumps({'smtp': {'port': 'not-a-number'}}),
                content_type='application/json',
            )
    assert resp.status_code == 400
    assert 'SMTP port' in resp.get_json()['message']


def test_get_settings_search_defaults(client, app):
    with app.app_context():
        with patch('src.routes.api.settings.setting.get_all_masked', return_value={}):
            resp = client.get('/api/settings')
    data = resp.get_json()['data']['search']
    assert data['defaultCabinClass'] == 'ECONOMY'
    assert data['defaultMaxStops'] == 'ANY'
    assert data['defaultAirlines'] == ''


def test_patch_settings_updates_search_defaults(client, app):
    with app.app_context():
        with patch('src.routes.api.settings.setting.get_all_masked', return_value={}):
            with patch('src.routes.api.settings.setting.set_many') as mock_set:
                resp = client.patch(
                    '/api/settings',
                    data=json.dumps(
                        {
                            'search': {
                                'default_cabin_class': 'business',
                                'default_max_stops': 'NON_STOP',
                                'default_airlines': ['cx', 'jl'],
                            }
                        }
                    ),
                    content_type='application/json',
                )
    assert resp.status_code == 200
    namespace, values = mock_set.call_args.args
    assert namespace == 'search'
    assert values['default_cabin_class'] == 'BUSINESS'
    assert values['default_max_stops'] == 'NON_STOP'
    assert values['default_airlines'] == 'CX,JL'


def test_patch_settings_invalid_search_enum_returns_400(client, app):
    with app.app_context():
        with patch('src.routes.api.settings.setting.get_all_masked', return_value={}):
            resp = client.patch(
                '/api/settings',
                data=json.dumps({'search': {'default_cabin_class': 'DELUXE'}}),
                content_type='application/json',
            )
    assert resp.status_code == 400
    assert resp.get_json()['success'] is False
