"""Database extension module for Flask-SQLAlchemy integration."""

from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy extension
db = SQLAlchemy()


def init_db(app):
    """Initialize database with Flask app context.

    Args:
        app: Flask application instance
    """
    db.init_app(app)

    with app.app_context():
        db.create_all()


def get_session():
    """Get current database session.

    Returns:
        SQLAlchemy session object
    """
    return db.session
