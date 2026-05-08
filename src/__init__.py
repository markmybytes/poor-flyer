from flask import Flask
import atexit
import os

from src.database import init_db
from src.routes.api import api_bp
from src.routes.pages import pages_bp
from src.scheduler import start_scheduler, stop_scheduler


def create_app():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(base_dir, "src", "templates")
    static_dir = os.path.join(base_dir, "src", "static")

    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

    init_db()

    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp)

    start_scheduler()
    atexit.register(stop_scheduler)

    return app
