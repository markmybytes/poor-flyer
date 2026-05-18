"""Flask extensions initialization module."""

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
    db.init_app(app)
    migrate.init_app(app, db, compare_type=True, render_as_batch=True)
    inertia.init_app(app)
    scheduler.init_app(app)
