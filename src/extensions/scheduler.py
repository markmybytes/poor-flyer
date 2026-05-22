"""Scheduler extension module for flask-apscheduler integration with Flask."""

import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from flask_apscheduler import APScheduler

logger = logging.getLogger(__name__)

scheduler = APScheduler(scheduler=BlockingScheduler())


def create_cron_trigger(expr: str, jitter: int = 0) -> CronTrigger:
    """Helper to create a CronTrigger from a crontab string with jitter."""
    t = CronTrigger.from_crontab(expr)
    t.jitter = jitter
    return t


def start_scheduler() -> None:
    """Start the APScheduler instance.

    When configured with BlockingScheduler, this call blocks until shutdown.
    """
    if not scheduler.running:
        logger.info('Starting APScheduler')
        scheduler.start()
    else:
        logger.debug('Scheduler already running, skipping start request')


def stop_scheduler() -> None:
    """Stop the APScheduler instance."""
    if scheduler.running:
        logger.info('Stopping APScheduler')
        scheduler.shutdown(wait=False)
    else:
        logger.debug('Scheduler not running, skipping stop request')


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
