"""
Configuration management service.
Provides type-safe access with in-memory caching to reduce DB overhead.
"""

import logging
from typing import Any

from src.extensions.database import Config, db

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Utility to manage app settings stored in the 'Config' table.
    Uses a class-level dictionary (_cache) for rapid lookups.
    """

    # In-memory store using (namespace, key) tuples as unique identifiers
    _cache: dict[tuple, Any] = {}
    _logger = logging.getLogger(__name__)

    @classmethod
    def get_str(cls, namespace: str, key: str, default: str | None = None) -> str | None:
        """
        Retrieves a setting as a string.
        Priority: Cache -> Database -> Default.
        """
        cache_key = (namespace, key)

        if cache_key in cls._cache:
            return cls._cache[cache_key]

        config = (
            db.session.query(Config)
            .filter(Config.namespace == namespace, Config.key == key)
            .first()
        )
        if config:
            cls._cache[cache_key] = config.value
            return config.value
        return default

    @classmethod
    def get_int(cls, namespace: str, key: str, default: int | None = None) -> int | None:
        """Helper to cast string settings to integers with error handling."""
        value = cls.get_str(namespace, key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            cls._logger.warning(f'Config {namespace}.{key} is not a valid integer: {value}')
            return default

    @classmethod
    def get_bool(cls, namespace: str, key: str, default: bool | None = None) -> bool | None:
        """Interprets truthy/falsy strings into actual boolean objects."""
        value = cls.get_str(namespace, key)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')

    @classmethod
    def set(cls, namespace: str, key: str, value: str) -> None:
        """
        Updates an existing key or creates a new one.
        Crucially invalidates the cache to prevent serving stale data.
        """
        cls.set_many(namespace, {key: value})

    @classmethod
    def set_many(cls, namespace: str, settings: dict[str, str]) -> None:
        """
        Bulk update multiple settings in a single transaction.
        More efficient than calling set() multiple times.
        """
        if not settings:
            return

        try:
            for key, value in settings.items():
                config = (
                    db.session.query(Config)
                    .filter(Config.namespace == namespace, Config.key == key)
                    .first()
                )
                if config:
                    config.value = value
                else:
                    config = Config(namespace=namespace, key=key, value=value)
                    db.session.add(config)

            db.session.commit()

            for key in settings.keys():
                cache_key = (namespace, key)
                if cache_key in cls._cache:
                    del cls._cache[cache_key]

            cls._logger.info(f'Bulk updated {len(settings)} settings in {namespace}')
        except Exception as e:
            db.session.rollback()
            cls._logger.error(f'Failed to bulk update config in {namespace}: {e}')
            raise

    @classmethod
    def get_all(cls, namespace: str) -> dict[str, str]:
        """
        Bulk fetch for a whole namespace.
        Handy for warming up the cache on startup.
        """
        configs = db.session.query(Config).filter(Config.namespace == namespace).all()
        result = {config.key: config.value for config in configs}

        for key, value in result.items():
            cls._cache[(namespace, key)] = value
        return result

    @classmethod
    def get_all_masked(cls, namespace: str) -> dict[str, str]:
        """Returns all config settings but hides sensitive password data."""
        data = cls.get_all(namespace)
        if 'password' in data:
            data['password'] = '***' if data['password'] else None
        return data

    @classmethod
    def clear_cache(cls) -> None:
        """Manually wipe the in-memory cache to force a DB refresh."""
        cls._cache.clear()
