# src/__init__.py
import logging
import os
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import Flask, current_app, g, request
from werkzeug.middleware.proxy_fix import ProxyFix

from src.cli import dev, run_scheduler
from src.extensions import init_extensions
from src.extensions.scheduler import create_cron_trigger
from src.logging_config import configure_logging
from src.routes.api import api_bp
from src.routes.pages import pages_bp
from src.utils.transform import CamelCaseJSONProvider

logger = logging.getLogger(__name__)


def _resolve_timezone():
    if tz := request.cookies.get('pf_timezone') or os.getenv('TZ'):
        try:
            g.tz = ZoneInfo(tz)
        except ZoneInfoNotFoundError:
            g.tz = ZoneInfo('UTC')
    else:
        g.tz = ZoneInfo('UTC')


def _inject_vite_url():
    """Context processor to inject vite_dev_url into Jinja templates."""
    vite_dev_url = None
    if current_app.debug:
        hot_file = current_app.config.get('VITE_HOT_FILE')
        if hot_file and Path(hot_file).exists():
            with open(hot_file) as f:
                vite_dev_url = f.read().strip()
    return {'vite_dev_url': vite_dev_url}


def create_app():
    """Application factory to initialize and configure the Flask app."""
    base_dir = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        template_folder=base_dir.joinpath('src', 'templates'),
        static_folder=base_dir.joinpath('src', 'static'),
    )

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    app.config.from_mapping(
        {
            'INERTIA_TEMPLATE': 'base.html',
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            'SCHEDULER_API_ENABLED': False,
            'LOG_LEVEL': os.getenv('PF_LOG_LEVEL', 'INFO'),
            'LOG_MAX_BYTES': int(os.getenv('PF_LOG_MAX_BYTES', str(10 * 1024 * 1024))),
            'LOG_FILE': os.getenv('PF_LOG_FILE', str(Path(app.instance_path).joinpath('app.log'))),
            'VITE_HOT_FILE': os.getenv(
                'PF_VITE_HOT_FILE', str(Path(app.static_folder).joinpath('dist', 'hot'))
            ),
            'SQLALCHEMY_DATABASE_URI': os.getenv(
                'PF_DATABASE_URL',
                os.getenv(
                    'DATABASE_PATH',
                    f'sqlite:///{Path(app.instance_path).joinpath("db.sqlite").as_posix()}',
                ),
            ),
            'JOBS': [
                {
                    'id': 'scrape_fares',
                    'func': 'src.services.scheduler:scrape_fares',
                    'trigger': create_cron_trigger(
                        os.getenv('PF_SCRAPE_CRON', '0 9 * * *'),
                        int(os.getenv('PF_SCRAPE_JITTER', 1800)),
                    ),
                },
                {
                    'id': 'disable_departured_itineraries',
                    'func': 'src.services.scheduler:disable_departured_itineraries',
                    'trigger': create_cron_trigger('0 0 * * *'),
                },
            ],
        }
    )

    if str(app.config['SQLALCHEMY_DATABASE_URI']).startswith('sqlite'):
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'connect_args': {'check_same_thread': False}}

    app.json = CamelCaseJSONProvider(app)

    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    configure_logging(app)
    logger.info('initializing Flask application')

    init_extensions(app)
    logger.info('extensions initialized')

    app.before_request(_resolve_timezone)

    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp)

    app.cli.add_command(dev)
    app.cli.add_command(run_scheduler)

    app.context_processor(_inject_vite_url)

    return app
