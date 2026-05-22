import logging

from flask import Blueprint, jsonify

from src.services import logs as log_svc

logger = logging.getLogger(__name__)

logs_api_bp = Blueprint('logs', __name__, url_prefix='/logs')


@logs_api_bp.route('', methods=['DELETE'])
def clear():
    try:
        log_svc.clear_logs()
        logger.info('Application logs cleared via API')
        return jsonify({'success': True})
    except Exception:
        logger.exception('Error clearing application logs')
        return jsonify({'success': False, 'message': 'Failed to clear logs'}), 500
