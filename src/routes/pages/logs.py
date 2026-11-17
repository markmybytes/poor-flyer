import logging
from contextlib import suppress
from datetime import date

from flask import Blueprint, redirect, request, session
from flask.typing import ResponseReturnValue
from flask_inertia import render_inertia

from src.services import logs as log_svc

logger = logging.getLogger(__name__)

logs_bp = Blueprint('logs', __name__, url_prefix='/logs')
VALID_LOG_LEVELS = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')


def _parse_date(d_str: str) -> date | None:
    with suppress(ValueError, TypeError):
        return date.fromisoformat(d_str)


@logs_bp.route('/')
def index() -> ResponseReturnValue:
    try:
        raw_levels = request.args.get('levels') or request.args.get('level', '')
        selected_levels = [
            lvl
            for lvl in (x.strip().upper() for x in raw_levels.split(','))
            if lvl in VALID_LOG_LEVELS
        ] or list(VALID_LOG_LEVELS)

        start_str, end_str = request.args.get('start_date', ''), request.args.get('end_date', '')

        all_logs = log_svc.read_logs(
            levels=selected_levels,
            start_date=_parse_date(start_str),
            end_date=_parse_date(end_str),
        )

        page, per_page = request.args.get('page', 1, type=int), 50
        start_idx = (page - 1) * per_page

        logger.debug(
            'rendered logs page: entries=%d page=%d levels=%s',
            len(all_logs),
            page,
            selected_levels,
        )
        return render_inertia(
            'Logs/Index',
            props={
                'logs': all_logs[start_idx : start_idx + per_page],
                'pagination': {'total': len(all_logs), 'page': page, 'per_page': per_page},
                'filters': {
                    'levels': selected_levels,
                    'start_date': start_str,
                    'end_date': end_str,
                },
            },
        )
    except Exception:
        logger.exception('render logs page failed')
        raise


@logs_bp.route('', methods=['DELETE'])
def clear() -> ResponseReturnValue:
    try:
        log_svc.clear_logs()
    except OSError:
        logger.exception('clear application logs from page failed')
        session['errors'] = {'logs': '清除紀錄失敗'}
        return redirect('/logs/')

    return redirect('/logs/')
