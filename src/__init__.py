import os

from flask import Flask, current_app
from flask_inertia import Inertia
from flask_migrate import Migrate

from src.cli import dev, run_scheduler
from src.database import DEFAULT_DATABASE_URL, db, init_db
from src.routes.api import api_bp
from src.routes.pages import pages_bp
from src.utils.json import CamelCaseJSONProvider

migrate = Migrate()


def _inject_vite_url():
    """Context processor to inject vite_dev_url into Jinja templates."""
    vite_dev_url = None
    if current_app.debug:
        hot_file = current_app.config.get('VITE_HOT_FILE')
        if hot_file and os.path.exists(hot_file):
            with open(hot_file) as f:
                vite_dev_url = f.read().strip()
    return {'vite_dev_url': vite_dev_url}


def create_app():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, 'src', 'templates'),
        static_folder=os.path.join(base_dir, 'src', 'static'),
    )

    app.config['INERTIA_TEMPLATE'] = 'base.html'
    app.config['VITE_HOT_FILE'] = os.path.join(app.static_folder, 'dist', 'hot')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', DEFAULT_DATABASE_URL)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    if db_uri.startswith('sqlite'):
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'connect_args': {'check_same_thread': False}}

    app.json = CamelCaseJSONProvider(app)

    init_db()
    db.init_app(app)
    migrate.init_app(app, db, compare_type=True, render_as_batch=True)
    Inertia(app)

    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp)

    app.cli.add_command(dev)
    app.cli.add_command(run_scheduler)

    app.context_processor(_inject_vite_url)

    return app
