from flask import Blueprint

from .itinerary import itineraries_bp
from .logs import logs_api_bp
from .lookup import lookup_bp
from .settings import settings_bp

api_bp = Blueprint('api', __name__, url_prefix='/api')

api_bp.register_blueprint(itineraries_bp)
api_bp.register_blueprint(settings_bp)
api_bp.register_blueprint(logs_api_bp)
api_bp.register_blueprint(lookup_bp)
