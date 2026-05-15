from flask import Blueprint

from .flights import flights_bp
from .settings import settings_bp

api_bp = Blueprint('api', __name__, url_prefix='/api')

api_bp.register_blueprint(flights_bp)
api_bp.register_blueprint(settings_bp)
