from datetime import date

from flask import Blueprint, request
from flask_inertia import render_inertia

from src.services import logs as log_svc

logs_bp = Blueprint('logs', __name__, url_prefix='/logs')


@logs_bp.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    level = request.args.get('level', 'ALL')
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')

    start_date = None
    end_date = None

    if start_date_str:
        try:
            start_date = date.fromisoformat(start_date_str)
        except ValueError:
            pass

    if end_date_str:
        try:
            end_date = date.fromisoformat(end_date_str)
        except ValueError:
            pass

    result = log_svc.read_logs(
        page=page,
        per_page=per_page,
        level=level if level != 'ALL' else None,
        start_date=start_date,
        end_date=end_date,
    )

    return render_inertia(
        'Logs/Index',
        props={
            'logs': result['entries'],
            'pagination': {
                'total': result['total'],
                'page': result['page'],
                'per_page': result['per_page'],
            },
            'filters': {
                'level': level,
                'start_date': start_date_str,
                'end_date': end_date_str,
            },
        },
    )
