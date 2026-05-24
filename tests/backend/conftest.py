import os

import pytest

from src import create_app
from src.extensions.database import db as _db

INERTIA_HEADERS = {'X-Inertia': 'true', 'X-Inertia-Version': ''}


@pytest.fixture(scope='session')
def app():
    os.environ['PF_DATABASE_URL'] = 'sqlite:///:memory:'

    app = create_app()
    app.config.update(
        {
            'TESTING': True,
            'JOBS': [],
            'WTF_CSRF_ENABLED': False,
        }
    )

    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_db(app):
    with app.app_context():
        yield
        _db.session.rollback()
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()
        from src.extensions.cache import cache

        cache.clear()
