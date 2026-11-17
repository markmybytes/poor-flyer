import logging

from flask import Blueprint, jsonify

from src.services import logs as log_svc

logger = logging.getLogger(__name__)

logs_api_bp = Blueprint('logs', __name__, url_prefix='/logs')


@logs_api_bp.route('', methods=['DELETE'])
def clear():
    try:
        log_svc.clear_logs()
        logger.info('application logs cleared via API')
        return jsonify({'message': 'Logs cleared', 'data': None})
    except Exception:
        logger.exception('clear application logs failed')
        return jsonify({'message': 'Failed to clear logs', 'data': None}), 500
