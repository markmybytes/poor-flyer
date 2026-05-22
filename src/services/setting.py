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
        logger.warning(f'Config {namespace}.{key} is not a valid integer: {val}')
        return default


def get_bool(namespace: str, key: str, default: bool | None = None) -> bool | None:
    val = get(namespace, key)
    if val is None:
        return default
    return val.lower() in ('true', '1', 'yes', 'on')


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
        logger.info(f'Bulk updated {len(settings)} settings in {namespace}')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Failed to bulk update config in {namespace}: {e}')
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


def clear_cache() -> None:
    cache.delete_memoized(_fetch)
