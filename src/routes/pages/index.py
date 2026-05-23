import logging

from flask import Blueprint, redirect

logger = logging.getLogger(__name__)

index_bp = Blueprint('index', __name__)


@index_bp.route('/')
def index():
    logger.debug('Redirecting root to itineraries page')
    return redirect('/itineraries/')
