"""
Configuration management service.
Provides type-safe access with Flask-Caching to reduce DB overhead.
"""

import logging
from collections.abc import Mapping
from typing import Any

from sqlalchemy import select

from src.extensions.cache import cache
from src.extensions.database import Config, db
from src.services.errors import FieldIssue, InvalidFieldsError
from src.utils.transform import to_bool

logger = logging.getLogger(__name__)

_CURRENCY_FIELDS = ('base_currency', 'fxrates_api_key', 'cache_ttl')
_EMAIL_FIELDS = ('recipients',)
_ITINERARY_FIELDS = ('disable_departured_itineraries',)
_SMTP_FIELDS = ('host', 'port', 'user', 'sender_email', 'require_auth', 'protocol', 'password')


def _section(data: Mapping[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    """Pick one store section's fields out of the flat payload, keeping only submitted ones."""
    return {field: data[field] for field in fields if field in data}


@cache.memoize()
def _fetch(namespace: str, key: str) -> str | None:
    """Pure, parameter-isolated cache key target."""
    stmt = select(Config).where(Config.namespace == namespace, Config.key == key)
    config = db.session.execute(stmt).scalar_one_or_none()
    return config.value if config else None


def get(namespace: str, key: str, default: str | None = None) -> str | None:
    """
    Retrieves a setting as a string.
    Priority: Cache -> Database -> Default.
    """
    val = _fetch(namespace, key)
    return val if val is not None else default


def get_int(namespace: str, key: str, default: int | None = None) -> int | None:
    val = get(namespace, key)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        logger.warning('invalid integer setting: namespace=%s key=%s value=%s', namespace, key, val)
        return default


def get_bool(namespace: str, key: str, default: bool | None = None) -> bool | None:
    val = get(namespace, key)
    if val is None:
        return default
    return to_bool(val)


def set(namespace: str, key: str, value: str) -> None:
    set_many(namespace, {key: value})


def set_many(namespace: str, settings: dict[str, str]) -> None:
    if not settings:
        return
    try:
        for key, value in settings.items():
            stmt = select(Config).where(Config.namespace == namespace, Config.key == key)
            config = db.session.execute(stmt).scalar_one_or_none()
            if config:
                config.value = value
            else:
                db.session.add(Config(namespace=namespace, key=key, value=value))
        db.session.commit()
        for key in settings:
            cache.delete_memoized(_fetch, namespace, key)
        logger.info(
            'updated configuration settings: namespace=%s count=%d', namespace, len(settings)
        )
    except Exception:
        db.session.rollback()
        raise


def get_all(namespace: str) -> dict[str, str]:
    stmt = select(Config).where(Config.namespace == namespace)
    configs = db.session.execute(stmt).scalars().all()
    return {c.key: get(namespace, c.key, c.value) or c.value for c in configs}


def get_all_masked(namespace: str) -> dict[str, str]:
    data = get_all(namespace)
    if 'password' in data:
        data['password'] = '***' if data['password'] else None
    return data


def get_page_settings() -> dict[str, dict[str, Any]]:
    """Settings payloads for the page props, with flags and numbers typed.

    Stored values are strings (legacy rows may hold 'true' or '587'); the page receives
    booleans and ints so the frontend bindings do not re-parse tokens.
    """
    currency = get_all_masked('currency')
    currency['base_currency'] = currency.get('base_currency') or 'HKD'
    currency['cache_ttl'] = get_int('currency', 'cache_ttl', 86400)
    currency['fxrates_api_key'] = currency.get('fxrates_api_key') or ''

    itinerary = get_all_masked('itinerary')
    itinerary['disable_departured_itineraries'] = get_bool(
        'itinerary', 'disable_departured_itineraries', False
    )

    smtp = get_all_masked('smtp')
    if 'port' in smtp:
        smtp['port'] = get_int('smtp', 'port')
    if 'require_auth' in smtp:
        smtp['require_auth'] = get_bool('smtp', 'require_auth', True)

    return {
        'currency': currency,
        'email': get_all_masked('email'),
        'itinerary': itinerary,
        'smtp': smtp,
    }


def update(data: Mapping[str, Any]) -> None:  # noqa: C901, PLR0915 - one check per section
    """Apply a flat partial payload; raise InvalidFieldsError with every invalid value."""
    from src.services.fx_rates import SUPPORTED_CURRENCIES

    # validate every section before the first write: a bad value never leaves half a payload
    base: str | None = None
    ttl: int | None = None
    port: int | None = None
    errors: list[FieldIssue] = []
    if currency_data := _section(data, _CURRENCY_FIELDS):
        if 'base_currency' in currency_data:
            base = (currency_data.get('base_currency') or 'HKD').strip().upper()
            if base not in SUPPORTED_CURRENCIES:
                errors.append(FieldIssue('base_currency', '不支援的基準貨幣'))
        if 'cache_ttl' in currency_data:
            try:
                ttl = int(currency_data.get('cache_ttl'))
            except TypeError, ValueError:
                ttl = None
            if ttl is None or ttl <= 0:
                errors.append(FieldIssue('cache_ttl', '快取有效時間必須是大於 0 的整數'))
    if smtp_data := _section(data, _SMTP_FIELDS):
        if 'port' in smtp_data:
            try:
                port = int(smtp_data.get('port'))
            except TypeError, ValueError:
                port = None
            if port is None:
                errors.append(FieldIssue('port', 'SMTP 連接埠必須是整數'))

    if errors:
        raise InvalidFieldsError(errors)

    if currency_data:
        existing = (get_all_masked('currency') or {}).copy()
        if base is not None:
            existing['base_currency'] = base
        if ttl is not None:
            existing['cache_ttl'] = str(ttl)
        if 'fxrates_api_key' in currency_data:
            existing['fxrates_api_key'] = (currency_data.get('fxrates_api_key') or '').strip()
        set_many('currency', existing)

    if email_data := _section(data, _EMAIL_FIELDS):
        existing = (get_all_masked('email') or {}).copy()
        existing['recipients'] = email_data.get('recipients', '')
        set_many('email', existing)

    if itinerary_data := _section(data, _ITINERARY_FIELDS):
        existing = (get_all_masked('itinerary') or {}).copy()
        existing['disable_departured_itineraries'] = (
            'true' if to_bool(itinerary_data.get('disable_departured_itineraries')) else 'false'
        )
        set_many('itinerary', existing)

    if smtp_data:
        # password excluded from the merge base: the masked '***' placeholder
        # must never overwrite a stored password; only a re-typed value does
        existing = {
            k: v for k, v in (get_all_masked('smtp') or {}).copy().items() if k != 'password'
        }
        for field in ['host', 'user', 'sender_email', 'protocol']:
            if field in smtp_data:
                existing[field] = smtp_data.get(field, '')
        if port is not None:
            existing['port'] = str(port)
        if 'require_auth' in smtp_data:
            existing['require_auth'] = 'true' if to_bool(smtp_data.get('require_auth')) else 'false'
        submitted_pwd = smtp_data.get('password')
        if submitted_pwd:
            existing['password'] = submitted_pwd
        set_many('smtp', existing)


def clear_cache() -> None:
    cache.delete_memoized(_fetch)
