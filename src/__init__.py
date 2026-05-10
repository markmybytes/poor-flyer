import atexit
import os

from flask import Flask
from flask_inertia import Inertia

from src.cli import dev
from src.database import init_db
from src.routes.api import api_bp
from src.routes.pages import pages_bp
from src.services.scheduler import start_scheduler, stop_scheduler


def create_app():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, "src", "templates"),
        static_folder=os.path.join(base_dir, "src", "static"),
    )
    app.config["INERTIA_TEMPLATE"] = "base.html"
    app.config["VITE_PORT"] = int(os.environ.get("VITE_PORT", "5173"))

    init_db()
    Inertia(app)

    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp)

    app.cli.add_command(dev)

    start_scheduler()
    atexit.register(stop_scheduler)

    return app
