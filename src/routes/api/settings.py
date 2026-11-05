import logging

from flask import Blueprint, jsonify, render_template, request

from src.services import setting
from src.services.fx_rates import (
    SUPPORTED_CURRENCIES,
    FXRatesError,
    get_configured_base_currency,
    get_rates,
)
from src.utils.email import get_smtp_config, send_html_email

logger = logging.getLogger(__name__)
settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


@settings_bp.route('', methods=['GET'])
def get_settings():
    try:
        currency = setting.get_all_masked('currency') or {}
        currency['base_currency'] = currency.get('base_currency') or 'HKD'
        currency['cache_ttl'] = currency.get('cache_ttl') or '86400'
        currency['fxrates_api_key'] = currency.get('fxrates_api_key') or ''

        return jsonify(
            {
                'success': True,
                'data': {
                    'smtp': setting.get_all_masked('smtp') or {},
                    'email': setting.get_all_masked('email') or {},
                    'currency': currency,
                },
            }
        )
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@settings_bp.route('', methods=['PATCH'])
def patch_settings():
    try:
        data = request.get_json(silent=True) or {}

        if 'currency' in data and (currency_data := data['currency'] or {}):
            existing = (setting.get_all_masked('currency') or {}).copy()
            if 'base_currency' in currency_data:
                base = (currency_data.get('base_currency') or 'HKD').strip().upper()
                if base not in SUPPORTED_CURRENCIES:
                    return jsonify({'success': False, 'message': 'Unsupported base currency'}), 400
                existing['base_currency'] = base
            if 'cache_ttl' in currency_data:
                try:
                    ttl = int(currency_data.get('cache_ttl'))
                    if ttl <= 0:
                        raise ValueError
                    existing['cache_ttl'] = str(ttl)
                except (TypeError, ValueError):
                    return jsonify(
                        {'success': False, 'message': 'Cache TTL must be an integer greater than 0'}
                    ), 400
            if 'fxrates_api_key' in currency_data:
                existing['fxrates_api_key'] = (currency_data.get('fxrates_api_key') or '').strip()
            setting.set_many('currency', existing)

        if 'email' in data and (email_data := data['email'] or {}):
            existing = (setting.get_all_masked('email') or {}).copy()
            if 'recipients' in email_data:
                existing['recipients'] = email_data.get('recipients', '')
            setting.set_many('email', existing)

        if 'itinerary' in data and (itinerary_data := data['itinerary'] or {}):
            existing = (setting.get_all_masked('itinerary') or {}).copy()
            if 'disable_departured_itineraries' in itinerary_data:
                existing['disable_departured_itineraries'] = (
                    'true'
                    if itinerary_data.get('disable_departured_itineraries', False)
                    else 'false'
                )
            setting.set_many('itinerary', existing)

        if 'smtp' in data and (smtp_data := data['smtp'] or {}):
            existing = (setting.get_all_masked('smtp') or {}).copy()
            for field in ['host', 'user', 'sender_email', 'protocol']:
                if field in smtp_data:
                    existing[field] = smtp_data.get(field, '')
            if 'port' in smtp_data:
                try:
                    existing['port'] = str(int(smtp_data.get('port')))
                except (TypeError, ValueError):
                    return jsonify(
                        {'success': False, 'message': 'SMTP port must be an integer'}
                    ), 400
            if 'require_auth' in smtp_data:
                existing['require_auth'] = (
                    'true' if smtp_data.get('require_auth', True) in [True, 'true'] else 'false'
                )
            if 'password' in smtp_data:
                existing['password'] = smtp_data['password']
            setting.set_many('smtp', existing)

        return jsonify({'success': True, 'message': 'Settings updated successfully'})
    except Exception as e:
        logger.exception('Error patching settings')
        return jsonify({'success': False, 'message': str(e)}), 400


@settings_bp.route('/fx-rates/refresh', methods=['POST'])
def refresh_fx_rates():
    try:
        payload = request.get_json(silent=True) or {}
        base = (payload.get('base_currency') or get_configured_base_currency()).strip().upper()
        rates = get_rates(base, force_refresh=True)
        return jsonify(
            {
                'success': True,
                'message': 'Latest FX rates fetched successfully',
                'data': {
                    'base_currency': rates.get('base', base),
                    'last_updated': rates.get('last_updated'),
                    'rates': rates.get('rates', {}),
                },
            }
        )
    except FXRatesError as e:
        logger.warning('FX rates refresh failed: %s', e)
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.exception('Unexpected error refreshing FX rates')
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

        if send_html_email(
            get_smtp_config(),
            recipient,
            'PoorFlyer - Test Email',
            render_template('email/test_email.html'),
        ):
            return jsonify({'success': True, 'message': f'Test email sent to {recipient}'})
        return jsonify({'success': False, 'message': 'Failed to send test email.'}), 400
    except Exception as e:
        logger.exception('Error sending test email')
        return jsonify({'success': False, 'message': str(e)}), 400
