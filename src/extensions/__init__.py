"""Flask extensions initialization module."""

from pathlib import Path
from urllib.parse import urlparse

from flask import Flask
from flask_inertia import Inertia
from flask_migrate import Migrate

from src.extensions.database import db
from src.extensions.scheduler import scheduler

inertia = Inertia()
migrate = Migrate()


def init_extensions(app: Flask) -> None:
    """Initialize all Flask extensions with the app.

    Args:
        app: Flask application instance
    """
    db_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if db_url.startswith('sqlite:///'):
        db_path = Path(urlparse(db_url).path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db, compare_type=True, render_as_batch=True)
    inertia.init_app(app)
    scheduler.init_app(app)
