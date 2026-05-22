from flask import Blueprint, jsonify, render_template, request

from src.services import setting
from src.services.fx_rates import (
    SUPPORTED_CURRENCIES,
    FXRatesError,
    get_configured_base_currency,
    get_rates,
)
from src.utils.email import get_smtp_config, send_html_email

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


@settings_bp.route('', methods=['GET'])
def get_settings():
    try:
        currency = setting.get_all_masked('currency')
        currency['base_currency'] = currency.get('base_currency') or 'HKD'
        currency['cache_ttl'] = currency.get('cache_ttl') or '86400'
        currency['fxrates_api_key'] = currency.get('fxrates_api_key') or ''

        return jsonify(
            {
                'success': True,
                'data': {
                    'smtp': setting.get_all_masked('smtp'),
                    'email': setting.get_all_masked('email'),
                    'currency': currency,
                },
            }
        )
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@settings_bp.route('', methods=['POST'])
def update_settings():
    try:
        data = request.get_json(silent=True) or request.form.to_dict()

        if smtp := data.get('smtp', {}):
            port = smtp.get('port', 587)
            try:
                port = int(port)
            except (TypeError, ValueError):
                return jsonify({'success': False, 'message': 'SMTP port must be an integer'}), 400

            smtp_settings = {
                'host': smtp.get('host', ''),
                'port': str(port),
                'user': smtp.get('user', ''),
                'sender_email': smtp.get('sender_email', ''),
                'require_auth': 'true' if smtp.get('require_auth', True) else 'false',
                'protocol': smtp.get('protocol', 'STARTTLS'),
            }

            if smtp.get('password'):
                smtp_settings['password'] = smtp['password']

            setting.set_many('smtp', smtp_settings)

        if email := data.get('email', {}):
            setting.set_many('email', {'recipients': email.get('recipients', '')})

        if currency := data.get('currency', {}):
            base_currency = (currency.get('base_currency') or 'HKD').strip().upper()
            if base_currency not in SUPPORTED_CURRENCIES:
                return jsonify({'success': False, 'message': 'Unsupported base currency'}), 400

            cache_ttl_raw = currency.get('cache_ttl', 86400)
            try:
                cache_ttl = int(cache_ttl_raw)
            except (TypeError, ValueError):
                return jsonify({'success': False, 'message': 'Cache TTL must be an integer'}), 400

            if cache_ttl <= 0:
                return jsonify(
                    {'success': False, 'message': 'Cache TTL must be greater than 0'}
                ), 400

            setting.set_many(
                'currency',
                {
                    'base_currency': base_currency,
                    'cache_ttl': str(cache_ttl),
                    'fxrates_api_key': (currency.get('fxrates_api_key') or '').strip(),
                },
            )

        return jsonify({'success': True, 'message': 'Settings updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@settings_bp.route('', methods=['PATCH'])
def patch_settings():
    try:
        data = request.get_json(silent=True) or {}

        if 'smtp' in data and (smtp := data['smtp'] or {}):
            try:
                port = int(smtp.get('port', 587))
            except (TypeError, ValueError):
                return jsonify({'success': False, 'message': 'SMTP port must be an integer'}), 400
            cfg = {k: smtp.get(k, '') for k in ['host', 'user', 'sender_email', 'protocol']}
            cfg.update(
                {
                    'port': str(port),
                    'require_auth': 'true' if smtp.get('require_auth', True) else 'false',
                }
            )
            if smtp.get('password'):
                cfg['password'] = smtp['password']
            setting.set_many('smtp', cfg)

        if 'email' in data and (email := data['email'] or {}):
            setting.set_many('email', {'recipients': email.get('recipients', '')})

        if 'currency' in data and (currency := data['currency'] or {}):
            base = (currency.get('base_currency') or 'HKD').strip().upper()
            if base not in SUPPORTED_CURRENCIES:
                return jsonify({'success': False, 'message': 'Unsupported base currency'}), 400
            try:
                ttl = int(currency.get('cache_ttl', 86400))
            except (TypeError, ValueError):
                return jsonify({'success': False, 'message': 'Cache TTL must be an integer'}), 400

            if ttl <= 0:
                return jsonify(
                    {'success': False, 'message': 'Cache TTL must be greater than 0'}
                ), 400
            setting.set_many(
                'currency',
                {
                    'base_currency': base,
                    'cache_ttl': str(ttl),
                    'fxrates_api_key': (currency.get('fxrates_api_key') or '').strip(),
                },
            )

        return jsonify({'success': True, 'message': 'Settings updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@settings_bp.route('/fx-rates/refresh', methods=['POST'])
def refresh_fx_rates():
    try:
        payload = request.get_json(silent=True) or {}
        base_currency = (
            (payload.get('base_currency') or get_configured_base_currency()).strip().upper()
        )
        rates = get_rates(base_currency, force_refresh=True)
        return jsonify(
            {
                'success': True,
                'message': 'Latest FX rates fetched successfully',
                'data': {
                    'base_currency': rates.get('base', base_currency),
                    'last_updated': rates.get('last_updated'),
                    'source': rates.get('source'),
                    'rates': rates.get('rates', {}),
                },
            }
        )
    except FXRatesError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@settings_bp.route('/test-email', methods=['POST'])
def test_email():
    try:
        data = request.get_json(silent=True) or request.form.to_dict()
        recipient = data.get('recipient', '').strip()

        if not recipient:
            return jsonify(
                {'success': False, 'message': 'Recipient email address is required'}
            ), 400

        success = send_html_email(
            get_smtp_config(),
            recipient,
            'PoorFlyer - Test Email',
            render_template('email/test_email.html'),
        )

        if success:
            return jsonify({'success': True, 'message': f'Test email sent to {recipient}'})
        return jsonify(
            {
                'success': False,
                'message': 'Failed to send test email. Check SMTP configuration and logs.',
            }
        ), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400
