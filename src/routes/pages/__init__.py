from flask import Blueprint

from .index import index_bp
from .itinerary import itineraries_bp
from .logs import logs_bp
from .settings import settings_bp

pages_bp = Blueprint('pages', __name__)

pages_bp.register_blueprint(index_bp)
pages_bp.register_blueprint(itineraries_bp)
pages_bp.register_blueprint(settings_bp)
pages_bp.register_blueprint(logs_bp)
