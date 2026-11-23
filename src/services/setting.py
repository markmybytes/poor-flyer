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
    """Complete settings payloads for the page props, with flags and numbers typed.

    Stored values are strings (legacy rows may hold 'true' or '587'); the page receives
    every key with its default, booleans and ints, so the frontend bindings do not re-parse
    tokens or invent fallbacks. The password is write-only: the page always sees ''.
    """
    currency = get_all_masked('currency')
    currency['base_currency'] = currency.get('base_currency') or 'HKD'
    currency['cache_ttl'] = get_int('currency', 'cache_ttl', 86400)
    currency['fxrates_api_key'] = currency.get('fxrates_api_key') or ''

    email = get_all_masked('email')
    email['recipients'] = email.get('recipients') or ''

    itinerary = get_all_masked('itinerary')
    itinerary['disable_departured_itineraries'] = get_bool(
        'itinerary', 'disable_departured_itineraries', False
    )

    smtp = get_all_masked('smtp')
    smtp['host'] = smtp.get('host') or ''
    smtp['port'] = get_int('smtp', 'port', 587)
    smtp['user'] = smtp.get('user') or ''
    smtp['password'] = ''
    smtp['sender_email'] = smtp.get('sender_email') or ''
    smtp['require_auth'] = get_bool('smtp', 'require_auth', True)
    smtp['protocol'] = smtp.get('protocol') or 'STARTTLS'

    return {
        'currency': currency,
        'email': email,
        'itinerary': itinerary,
        'smtp': smtp,
    }


def update(data: Mapping[str, Any]) -> None:  # noqa: C901, PLR0915 - one check per section
    """Apply a nested partial payload; raise InvalidFieldsError with every invalid value."""
    from src.services.fx_rates import SUPPORTED_CURRENCIES

    # validate every section before the first write: a bad value never leaves half a payload
    base: str | None = None
    ttl: int | None = None
    port: int | None = None
    errors: list[FieldIssue] = []
    if currency_data := data.get('currency') or {}:
        if 'base_currency' in currency_data:
            base = (currency_data.get('base_currency') or 'HKD').strip().upper()
            if base not in SUPPORTED_CURRENCIES:
                errors.append(FieldIssue('currency.base_currency', '不支援的基準貨幣'))
        if 'cache_ttl' in currency_data:
            try:
                ttl = int(currency_data.get('cache_ttl'))
            except TypeError, ValueError:
                ttl = None
            if ttl is None or ttl <= 0:
                errors.append(FieldIssue('currency.cache_ttl', '快取有效時間必須是大於 0 的整數'))
    if smtp_data := data.get('smtp') or {}:
        if 'port' in smtp_data:
            try:
                port = int(smtp_data.get('port'))
            except TypeError, ValueError:
                port = None
            if port is None:
                errors.append(FieldIssue('smtp.port', 'SMTP 連接埠必須是整數'))

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

    if email_data := data.get('email') or {}:
        existing = (get_all_masked('email') or {}).copy()
        if 'recipients' in email_data:
            existing['recipients'] = email_data.get('recipients', '')
        set_many('email', existing)

    if itinerary_data := data.get('itinerary') or {}:
        existing = (get_all_masked('itinerary') or {}).copy()
        if 'disable_departured_itineraries' in itinerary_data:
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
