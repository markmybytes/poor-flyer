from flask import Blueprint
from flask_inertia import render_inertia

from src.services import config
from src.services.fx_rates import (
    SUPPORTED_CURRENCIES,
    FXRatesError,
    get_configured_base_currency,
    get_rates,
)

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


@settings_bp.route('/')
def index():
    base_currency = get_configured_base_currency()

    try:
        rates_snapshot = get_rates(base_currency)
        fx_status = {
            'base_currency': rates_snapshot.get('base', base_currency),
            'last_updated': rates_snapshot.get('last_updated'),
            'source': rates_snapshot.get('source'),
            'rates': rates_snapshot.get('rates', {}),
            'error': None,
        }
    except FXRatesError as exc:
        fx_status = {
            'base_currency': base_currency,
            'last_updated': None,
            'source': None,
            'rates': {},
            'error': str(exc),
        }

    currency_settings = config.get_all_masked('currency')
    currency_settings['base_currency'] = currency_settings.get('base_currency', base_currency)
    currency_settings['cache_ttl'] = currency_settings.get('cache_ttl', '86400')
    currency_settings['fxrates_api_key'] = currency_settings.get('fxrates_api_key', '')

    return render_inertia(
        'Settings/Index',
        props={
            'settings': {
                'smtp': config.get_all_masked('smtp'),
                'email': config.get_all_masked('email'),
                'currency': currency_settings,
            },
            'supportedCurrencies': SUPPORTED_CURRENCIES,
            'fxStatus': fx_status,
        },
    )
