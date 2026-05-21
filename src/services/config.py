"""
Configuration management service.
Provides type-safe access with Flask-Caching to reduce DB overhead.
"""

import logging

from sqlalchemy import select

from src.extensions.cache import cache
from src.extensions.database import Config, db

logger = logging.getLogger(__name__)


@cache.memoize()
def get_str(namespace: str, key: str, default: str | None = None) -> str | None:
    """
    Retrieves a setting as a string.
    Priority: Cache -> Database -> Default.
    """
    stmt = select(Config).where(Config.namespace == namespace, Config.key == key)
    config = db.session.execute(stmt).scalar_one_or_none()
    if config:
        return config.value
    return default


def get_int(namespace: str, key: str, default: int | None = None) -> int | None:
    """Helper to cast string settings to integers with error handling."""
    value = get_str(namespace, key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning(f'Config {namespace}.{key} is not a valid integer: {value}')
        return default


def get_bool(namespace: str, key: str, default: bool | None = None) -> bool | None:
    """Interprets truthy/falsy strings into actual boolean objects."""
    value = get_str(namespace, key)
    if value is None:
        return default
    return value.lower() in ('true', '1', 'yes', 'on')


def set(namespace: str, key: str, value: str) -> None:
    """
    Updates an existing key or creates a new one.
    Crucially invalidates the cache to prevent serving stale data.
    """
    set_many(namespace, {key: value})


def set_many(namespace: str, settings: dict[str, str]) -> None:
    """
    Bulk update multiple settings in a single transaction.
    More efficient than calling set() multiple times.
    """
    if not settings:
        return

    try:
        for key, value in settings.items():
            stmt = select(Config).where(Config.namespace == namespace, Config.key == key)
            config = db.session.execute(stmt).scalar_one_or_none()
            if config:
                config.value = value
            else:
                config = Config(namespace=namespace, key=key, value=value)
                db.session.add(config)

        db.session.commit()

        for key in settings:
            cache.delete_memoized(get_str, namespace, key)

        logger.info(f'Bulk updated {len(settings)} settings in {namespace}')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Failed to bulk update config in {namespace}: {e}')
        raise


def get_all(namespace: str) -> dict[str, str]:
    """
    Bulk fetch for a whole namespace.
    Uses get_str() to keep cache as the single source of truth.
    """
    stmt = select(Config).where(Config.namespace == namespace)
    configs = db.session.execute(stmt).scalars().all()
    return {
        config.key: get_str(namespace, config.key, config.value) or config.value
        for config in configs
    }


def get_all_masked(namespace: str) -> dict[str, str]:
    """Returns all config settings but hides sensitive password data."""
    data = get_all(namespace)
    if 'password' in data:
        data['password'] = '***' if data['password'] else None
    return data


def clear_cache() -> None:
    """Manually wipe memoized values to force DB refresh."""
    cache.delete_memoized(get_str)
