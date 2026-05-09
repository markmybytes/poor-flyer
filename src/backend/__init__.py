import atexit
import os

from flask import Flask
from flask_inertia import Inertia
from src.backend.database import init_db
from src.backend.routes.api import api_bp
from src.backend.routes.pages import pages_bp
from src.backend.services.scheduler import start_scheduler, stop_scheduler


def create_app():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, "src", "backend", "templates"),
        static_folder=os.path.join(base_dir, "src", "backend", "static"),
    )

    app.config["INERTIA_TEMPLATE"] = "base.html"

    init_db()

    Inertia(app)

    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp)

    start_scheduler()
    atexit.register(stop_scheduler)

    return app
