import logging

from flask import Blueprint, make_response, redirect, request
from flask_inertia import render_inertia

from src.services import setting
from src.services.fx_rates import (
    SUPPORTED_CURRENCIES,
    FXRatesError,
    get_configured_base_currency,
    get_rates,
)

logger = logging.getLogger(__name__)

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


def _index_props() -> dict:
    base_currency = get_configured_base_currency()

    try:
        rates_snapshot = get_rates(base_currency)
        fx_status = {
            'base_currency': rates_snapshot.get('base', base_currency),
            'last_updated': rates_snapshot.get('last_updated'),
            'rates': rates_snapshot.get('rates', {}),
            'error': None,
        }
    except FXRatesError as exc:
        logger.warning('load fx rates for settings page failed: error=%s', type(exc).__name__)
        fx_status = {
            'base_currency': base_currency,
            'last_updated': None,
            'rates': {},
            'error': str(exc),
        }

    currency_settings = setting.get_all_masked('currency')
    currency_settings['base_currency'] = currency_settings.get('base_currency', base_currency)
    currency_settings['cache_ttl'] = currency_settings.get('cache_ttl', '86400')
    currency_settings['fxrates_api_key'] = currency_settings.get('fxrates_api_key', '')

    return {
        'settings': {
            'currency': currency_settings,
            'email': setting.get_all_masked('email'),
            'itinerary': setting.get_all_masked('itinerary'),
            'smtp': setting.get_all_masked('smtp'),
        },
        'supportedCurrencies': SUPPORTED_CURRENCIES,
        'fxStatus': fx_status,
    }


@settings_bp.route('/')
def index():
    return render_inertia('Settings/Index', props=_index_props())


@settings_bp.route('', methods=['POST'])
def save():
    try:
        setting.update(request.get_json(silent=True) or request.form.to_dict())
    except ValueError as exc:
        # shortcut: full props re-render for Inertia 422; may block up to 15s on a
        # cold FX cache when the network is unreachable (get_rates stale fallback)
        response = make_response(
            render_inertia(
                'Settings/Index',
                props=_index_props() | {'errors': {'settings': str(exc)}},
            )
        )
        response.status_code = 422
        return response

    logger.info('Settings updated from page form')
    return redirect('/settings/')
