import os

from src.extensions.database import DEFAULT_DATABASE_URL


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def get_app_config() -> dict[str, object]:
    return {
        'INERTIA_TEMPLATE': os.getenv('INERTIA_TEMPLATE', 'base.html'),
        'SQLALCHEMY_DATABASE_URI': os.getenv('DATABASE_URL', DEFAULT_DATABASE_URL),
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SCHEDULER_API_ENABLED': False,
        'SCHEDULER_TIMEZONE': os.getenv('SCHEDULER_TIMEZONE', 'UTC'),
        'SCHEDULER_SCRAPE_CRON_HOUR': _env_int('SCHEDULER_SCRAPE_CRON_HOUR', 9),
        'SCHEDULER_SCRAPE_CRON_MINUTE': _env_int('SCHEDULER_SCRAPE_CRON_MINUTE', 0),
        'SCHEDULER_SCRAPE_JITTER_SECONDS': _env_int('SCHEDULER_SCRAPE_JITTER_SECONDS', 1800),
    }
