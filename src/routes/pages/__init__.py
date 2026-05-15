from flask import Blueprint

from .flights import flights_bp
from .index import index_bp
from .settings import settings_bp

pages_bp = Blueprint('pages', __name__)

pages_bp.register_blueprint(index_bp)
pages_bp.register_blueprint(flights_bp)
pages_bp.register_blueprint(settings_bp)
