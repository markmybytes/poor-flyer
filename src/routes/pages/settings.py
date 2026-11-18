import logging

from flask import Blueprint, flash, g, redirect, session
from flask_inertia import render_inertia

from src.schemas.settings import SettingsPayload
from src.services import setting
from src.services.fx_rates import (
    SUPPORTED_CURRENCIES,
    FXRatesError,
    get_configured_base_currency,
    get_rates,
)
from src.validation import validated

logger = logging.getLogger(__name__)

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


@settings_bp.route('/')
def index():
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

    return render_inertia(
        'Settings/Index',
        props={
            'settings': setting.get_page_settings(),
            'supportedCurrencies': SUPPORTED_CURRENCIES,
            'fxStatus': fx_status,
        },
    )


@settings_bp.route('', methods=['POST'])
@validated(SettingsPayload, error_key='settings', redirect_to='/settings/')
def save():
    try:
        setting.update(g.validated.model_dump(exclude_unset=True))
        logger.info('settings updated from page form')

        flash('設定已儲存', 'success')
        return redirect('/settings/')
    except ValueError as exc:
        session['errors'] = {'settings': str(exc)}
        return redirect('/settings/')
