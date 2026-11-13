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
    return val.lower() in ('1', 'enable', 'enabled', 'true', 'yes', 'y', 'on')


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


def update(data: Mapping[str, Any]) -> None:
    """Apply a partial settings payload, raising ValueError on invalid values."""
    from src.services.fx_rates import SUPPORTED_CURRENCIES

    if 'currency' in data and (currency_data := data['currency'] or {}):
        existing = (get_all_masked('currency') or {}).copy()
        if 'base_currency' in currency_data:
            base = (currency_data.get('base_currency') or 'HKD').strip().upper()
            if base not in SUPPORTED_CURRENCIES:
                raise ValueError('Unsupported base currency')
            existing['base_currency'] = base
        if 'cache_ttl' in currency_data:
            try:
                ttl = int(currency_data.get('cache_ttl'))
            except TypeError, ValueError:
                raise ValueError('Cache TTL must be an integer greater than 0') from None
            if ttl <= 0:
                raise ValueError('Cache TTL must be an integer greater than 0')
            existing['cache_ttl'] = str(ttl)
        if 'fxrates_api_key' in currency_data:
            existing['fxrates_api_key'] = (currency_data.get('fxrates_api_key') or '').strip()
        set_many('currency', existing)

    if 'email' in data and (email_data := data['email'] or {}):
        existing = (get_all_masked('email') or {}).copy()
        if 'recipients' in email_data:
            existing['recipients'] = email_data.get('recipients', '')
        set_many('email', existing)

    if 'itinerary' in data and (itinerary_data := data['itinerary'] or {}):
        existing = (get_all_masked('itinerary') or {}).copy()
        if 'disable_departured_itineraries' in itinerary_data:
            existing['disable_departured_itineraries'] = (
                'true' if itinerary_data.get('disable_departured_itineraries', False) else 'false'
            )
        set_many('itinerary', existing)

    if 'smtp' in data and (smtp_data := data['smtp'] or {}):
        # password excluded from the merge base: the masked '***' placeholder
        # must never overwrite a stored password; only a re-typed value does
        existing = {
            k: v for k, v in (get_all_masked('smtp') or {}).copy().items() if k != 'password'
        }
        for field in ['host', 'user', 'sender_email', 'protocol']:
            if field in smtp_data:
                existing[field] = smtp_data.get(field, '')
        if 'port' in smtp_data:
            try:
                existing['port'] = str(int(smtp_data.get('port')))
            except TypeError, ValueError:
                raise ValueError('SMTP port must be an integer') from None
        if 'require_auth' in smtp_data:
            existing['require_auth'] = (
                'true' if smtp_data.get('require_auth', True) in [True, 'true'] else 'false'
            )
        submitted_pwd = smtp_data.get('password')
        if submitted_pwd:
            existing['password'] = submitted_pwd
        set_many('smtp', existing)


def clear_cache() -> None:
    cache.delete_memoized(_fetch)
