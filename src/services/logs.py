"""
Log file reading, filtering, and management service.
"""

import logging
import re
from collections.abc import Iterator
from datetime import date
from pathlib import Path

from flask import current_app

logger = logging.getLogger(__name__)

_LOG_ENTRY_RE = re.compile(
    r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})'
    r' - (DEBUG|INFO|WARNING|ERROR|CRITICAL) - (.+?) - (.*)$'
)


def _log_path() -> Path:
    return Path(current_app.config['LOG_FILE'])


def _iter_log_entries(path: Path) -> Iterator[dict]:
    """Generator that yields parsed log entries one by one to save memory."""
    with path.open(encoding='utf-8', errors='replace') as f:
        current: dict | None = None
        for line in f:
            line = line.rstrip('\n')

            if (match := _LOG_ENTRY_RE.match(line)) is not None:
                if current is not None:
                    yield current

                current = dict(
                    zip(('timestamp', 'level', 'logger', 'message'), match.groups(), strict=True),
                    traceback=None,
                )
            elif current is not None:
                current['traceback'] = (
                    line if current['traceback'] is None else current['traceback'] + '\n' + line
                )

        if current is not None:
            yield current


def read_logs(
    levels: list[str] | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    path = _log_path()
    if not path.exists():
        logger.debug('Log file not found: path=%s', path)
        return []

    level_set = set(levels) if levels else None
    start_str = start_date.isoformat() if start_date else None
    end_str = end_date.isoformat() if end_date else None

    filtered_entries = []

    for entry in _iter_log_entries(path):
        if level_set and entry['level'] not in level_set:
            continue

        entry_date_str = entry['timestamp'][:10]
        if start_str and entry_date_str < start_str:
            continue
        if end_str and entry_date_str > end_str:
            continue

        filtered_entries.append(entry)

    filtered_entries.reverse()

    logger.debug(
        'Read logs: total_entries=%d levels=%s start_date=%s end_date=%s',
        len(filtered_entries),
        levels,
        start_date,
        end_date,
    )
    return filtered_entries


def clear_logs() -> None:
    try:
        if (path := _log_path()).exists():
            path.write_text('', encoding='utf-8')
            logger.info('Application logs cleared')
    except Exception:
        logger.exception('Error clearing logs')
