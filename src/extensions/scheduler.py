"""Scheduler extension module for flask-apscheduler integration with Flask."""

import logging

from flask_apscheduler import APScheduler

logger = logging.getLogger(__name__)

scheduler = APScheduler()


def start_scheduler() -> None:
    """Start the APScheduler instance."""
    if not scheduler.running:
        scheduler.start()
        logger.info('Scheduler started')


def stop_scheduler() -> None:
    """Stop the APScheduler instance."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info('Scheduler stopped')


def get_scheduler():
    """Get the APScheduler instance.

    Returns:
        APScheduler instance
    """
    return scheduler


def is_running():
    """Check if scheduler is running.

    Returns:
        bool: True if scheduler is running, False otherwise
    """
    return scheduler.running
