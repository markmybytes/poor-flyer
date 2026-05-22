from datetime import date

from flask import Blueprint, request
from flask_inertia import render_inertia

from src.services import logs as log_svc

logs_bp = Blueprint('logs', __name__, url_prefix='/logs')
VALID_LOG_LEVELS = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')


@logs_bp.route('/')
def index():
    if levels_raw := request.args.get('levels', ''):
        selected_levels = [
            lvl
            for lvl in [x.strip().upper() for x in levels_raw.split(',')]
            if lvl in VALID_LOG_LEVELS
        ]
    else:
        level = request.args.get('level', 'ALL').strip().upper()
        selected_levels = [level] if level in VALID_LOG_LEVELS else list(VALID_LOG_LEVELS)

    if not selected_levels:
        selected_levels = list(VALID_LOG_LEVELS)

    start_date, end_date = None, None
    if start_date_str := request.args.get('start_date', ''):
        try:
            start_date = date.fromisoformat(start_date_str)
        except ValueError:
            pass

    if end_date_str := request.args.get('end_date', ''):
        try:
            end_date = date.fromisoformat(end_date_str)
        except ValueError:
            pass

    result = log_svc.read_logs(
        page=request.args.get('page', 1, type=int),
        per_page=50,
        levels=selected_levels,
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
                'levels': selected_levels,
                'start_date': start_date_str,
                'end_date': end_date_str,
            },
        },
    )
