"""Scheduler extension module for APScheduler integration with Flask."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask

logger = logging.getLogger(__name__)

# Initialize scheduler
scheduler = BackgroundScheduler(daemon=True)


def configure_scheduler(app: Flask) -> None:
    """Configure APScheduler with Flask app and register jobs.

    Args:
        app: Flask application instance
    """
    if scheduler.get_job('daily_scrape') is not None:
        return

    from src.services.scheduler import daily_scrape_job

    scheduler.add_job(
        id='daily_scrape',
        func=daily_scrape_job,
        trigger='cron',
        hour=app.config['SCHEDULER_SCRAPE_CRON_HOUR'],
        minute=app.config['SCHEDULER_SCRAPE_CRON_MINUTE'],
        jitter=app.config['SCHEDULER_SCRAPE_JITTER_SECONDS'],
        name='Daily flight price scrape',
        coalesce=True,
        max_instances=1,
        timezone=app.config['SCHEDULER_TIMEZONE'],
    )


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
        BackgroundScheduler instance
    """
    return scheduler


def is_running():
    """Check if scheduler is running.

    Returns:
        bool: True if scheduler is running, False otherwise
    """
    return scheduler.running
