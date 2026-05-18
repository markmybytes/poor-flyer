"""Scheduler extension module for APScheduler integration."""

import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

# Initialize scheduler
scheduler = BackgroundScheduler(daemon=True)


def init_scheduler(app):
    """Initialize scheduler with Flask app configuration.

    Args:
        app: Flask application instance
    """
    from src.services.scheduler import start_scheduler

    try:
        start_scheduler()
        logger.info(f'Scheduler initialized at {datetime.now()}')
    except Exception as e:
        logger.error(f'Failed to initialize scheduler: {e}', exc_info=True)


def get_scheduler():
    """Get the APScheduler instance.

    Returns:
        BackgroundScheduler instance
    """
    return scheduler


def is_running():
    """Check if scheduler is running.

    Returns:
        bool: True if scheduler is running, False otherwise
    """
    return scheduler.running
