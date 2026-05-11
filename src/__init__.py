import atexit
import os

from flask import Flask, current_app
from flask_inertia import Inertia

from src.cli import dev
from src.database import init_db
from src.routes.api import api_bp
from src.routes.pages import pages_bp
from src.services.scheduler import start_scheduler, stop_scheduler


def _inject_vite_url():
    """Context processor to inject vite_dev_url into Jinja templates."""
    vite_dev_url = None
    if current_app.debug:
        hot_file = current_app.config.get("VITE_HOT_FILE")
        if hot_file and os.path.exists(hot_file):
            with open(hot_file, "r") as f:
                vite_dev_url = f.read().strip()
    return dict(vite_dev_url=vite_dev_url)


def create_app():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, "src", "templates"),
        static_folder=os.path.join(base_dir, "src", "static"),
    )

    app.config["INERTIA_TEMPLATE"] = "base.html"
    app.config["VITE_HOT_FILE"] = os.path.join(app.static_folder, "dist", "hot")

    init_db()
    Inertia(app)

    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp)

    app.cli.add_command(dev)

    app.context_processor(_inject_vite_url)

    start_scheduler()
    atexit.register(stop_scheduler)

    return app
