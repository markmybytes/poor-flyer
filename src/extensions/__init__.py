"""Flask extensions initialization module."""

import logging
from pathlib import Path

from flask import Flask
from flask_inertia import Inertia
from flask_migrate import Migrate

from src.extensions.cache import cache
from src.extensions.database import db
from src.extensions.scheduler import scheduler

logger = logging.getLogger(__name__)

inertia = Inertia()
migrate = Migrate()


def init_extensions(app: Flask) -> None:
    """Initialize all Flask extensions with the app.

    Args:
        app: Flask application instance
    """
    db_url = str(app.config.get('SQLALCHEMY_DATABASE_URI', ''))
    if db_url.startswith('sqlite:///'):
        sqlite_path = db_url.removeprefix('sqlite:///')
        if sqlite_path and sqlite_path != ':memory:':
            Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db, compare_type=True, render_as_batch=True)
    inertia.init_app(app)
    cache.init_app(app)
    scheduler.init_app(app)
