import logging

from flask import Blueprint
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


@settings_bp.route('/')
def index():
    try:
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
            logger.warning('Unable to load FX rates for settings page: %s', type(exc).__name__)
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

        search_settings = setting.get_all_masked('search')
        search_settings['default_cabin_class'] = search_settings.get(
            'default_cabin_class', 'ECONOMY'
        )
        search_settings['default_max_stops'] = search_settings.get('default_max_stops', 'ANY')
        search_settings['default_airlines'] = search_settings.get('default_airlines', '')
        search_settings['cache_ttl'] = search_settings.get('cache_ttl', '43200')

        return render_inertia(
            'Settings/Index',
            props={
                'settings': {
                    'currency': currency_settings,
                    'email': setting.get_all_masked('email'),
                    'itinerary': setting.get_all_masked('itinerary'),
                    'search': search_settings,
                    'smtp': setting.get_all_masked('smtp'),
                },
                'supportedCurrencies': SUPPORTED_CURRENCIES,
                'fxStatus': fx_status,
            },
        )
    except Exception:
        logger.exception('Error rendering settings page')
        raise
