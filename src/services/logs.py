"""
Log file reading, filtering, and management service.
"""

import re
from datetime import date, datetime
from pathlib import Path

from flask import current_app

_LOG_ENTRY_RE = re.compile(
    r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})'
    r' - (DEBUG|INFO|WARNING|ERROR|CRITICAL) - (.+?) - (.*)$'
)


def _log_path() -> Path:
    return Path(current_app.config['LOG_FILE'])


def _parse_entries(lines: list[str]) -> list[dict]:
    entries: list[dict] = []
    current: dict | None = None
    for line in lines:
        match = _LOG_ENTRY_RE.match(line)
        if match:
            if current is not None:
                entries.append(current)
            ts, level, logger_name, message = match.groups()
            current = {
                'timestamp': ts,
                'level': level,
                'logger': logger_name,
                'message': message,
                'traceback': None,
            }
        elif current is not None:
            current['traceback'] = (
                line if current['traceback'] is None else current['traceback'] + '\n' + line
            )
    if current is not None:
        entries.append(current)
    return entries


def read_logs(
    page: int = 1,
    per_page: int = 50,
    levels: list[str] | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    if not (path := _log_path()).exists():
        return {'entries': [], 'total': 0, 'page': page, 'per_page': per_page}

    with path.open(encoding='utf-8', errors='replace') as f:
        lines = [line.rstrip('\n') for line in f]

    entries = _parse_entries(lines)
    entries.reverse()

    if levels:
        level_set = set(levels)
        entries = [e for e in entries if e['level'] in level_set]

    if start_date or end_date:
        filtered = []
        for e in entries:
            entry_date = datetime.strptime(e['timestamp'][:10], '%Y-%m-%d').date()
            if start_date and entry_date < start_date:
                continue
            if end_date and entry_date > end_date:
                continue
            filtered.append(e)
        entries = filtered

    total = len(entries)
    start_idx = (page - 1) * per_page
    return {
        'entries': entries[start_idx : start_idx + per_page],
        'total': total,
        'page': page,
        'per_page': per_page,
    }


def clear_logs() -> None:
    if (path := _log_path()).exists():
        path.write_text('', encoding='utf-8')
