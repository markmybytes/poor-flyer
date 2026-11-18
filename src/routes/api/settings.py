import logging

from flask import Blueprint, jsonify, render_template, request
from flask.typing import ResponseReturnValue

from src.services.fx_rates import (
    FXRatesError,
    get_configured_base_currency,
    get_rates,
)
from src.utils.email import get_smtp_config, send_html_email

logger = logging.getLogger(__name__)
settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


@settings_bp.route('/fx-rates/refresh', methods=['POST'])
def refresh_fx_rates() -> ResponseReturnValue:
    try:
        payload = request.get_json(silent=True) or {}
        base = (payload.get('base_currency') or get_configured_base_currency()).strip().upper()
        rates = get_rates(base, force_refresh=True)
        return jsonify(
            {
                'message': 'Latest FX rates fetched successfully',
                'data': {
                    'base_currency': rates.get('base', base),
                    'last_updated': rates.get('last_updated'),
                    'rates': rates.get('rates', {}),
                },
            }
        )
    except FXRatesError as e:
        logger.warning('fx rates refresh failed: error=%s', e)
        return jsonify({'message': str(e), 'data': None}), 400
    except Exception as e:
        logger.exception('refresh fx rates failed: reason=unexpected')
        return jsonify({'message': str(e), 'data': None}), 400


@settings_bp.route('/test-email', methods=['POST'])
def test_email() -> ResponseReturnValue:
    try:
        data = request.get_json(silent=True) or request.form.to_dict()
        recipient = data.get('recipient', '').strip()
        if not recipient:
            return jsonify({'message': 'Recipient email address is required', 'data': None}), 400

        if send_html_email(
            get_smtp_config(),
            recipient,
            'PoorFlyer - Test Email',
            render_template('email/test_email.html'),
        ):
            return jsonify({'message': f'Test email sent to {recipient}', 'data': None})
        return jsonify({'message': 'Failed to send test email.', 'data': None}), 400
    except Exception as e:
        logger.exception('send test email failed')
        return jsonify({'message': str(e), 'data': None}), 400
