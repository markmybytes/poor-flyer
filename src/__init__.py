import os

from flask import Flask, current_app

from src.cli import dev, run_scheduler
from src.extensions import init_extensions
from src.extensions.database import DEFAULT_DATABASE_URL, init_db
from src.extensions.scheduler import configure_scheduler
from src.routes.api import api_bp
from src.routes.pages import pages_bp
from src.utils.json import CamelCaseJSONProvider


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

    app.config.from_mapping(
        {
            'SQLALCHEMY_DATABASE_URI': os.getenv('DATABASE_URL', DEFAULT_DATABASE_URL),
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            'SCHEDULER_API_ENABLED': False,
            'SCHEDULER_TIMEZONE': os.getenv('TZ'),
            'SCHEDULER_SCRAPE_CRON': os.getenv('SCHEDULER_SCRAPE_CRON', '0 9 * * *'),
            'SCHEDULER_SCRAPE_JITTER_SECONDS': int(os.getenv('SCHEDULER_SCRAPE_JITTER_SECONDS', 0)),
        }
    )

    app.config['VITE_HOT_FILE'] = os.getenv(
        'VITE_HOT_FILE',
        os.path.join(app.static_folder, 'dist', 'hot'),
    )

    app.json = CamelCaseJSONProvider(app)

    db_uri = str(app.config['SQLALCHEMY_DATABASE_URI'])
    if db_uri.startswith('sqlite'):
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'connect_args': {'check_same_thread': False}}

    init_db()
    init_extensions(app)
    configure_scheduler(app)

    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp)

    app.cli.add_command(dev)
    app.cli.add_command(run_scheduler)

    app.context_processor(_inject_vite_url)

    return app
