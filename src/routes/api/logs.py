from flask import Blueprint, jsonify

from src.services import logs as log_svc

logs_api_bp = Blueprint('logs', __name__, url_prefix='/logs')


@logs_api_bp.route('', methods=['DELETE'])
def clear():
    try:
        log_svc.clear_logs()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
