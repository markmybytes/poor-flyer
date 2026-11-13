"""Root-logger configuration, log-file trimming, and request correlation ids."""

import copy
import logging
import os
import uuid
from contextvars import ContextVar
from pathlib import Path

from flask import Flask

LOG_FORMAT = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'

# Third-party loggers stay quiet except for APScheduler's lifecycle messages.
QUIET_LOGGERS = {
    'werkzeug': logging.WARNING,
    'urllib3': logging.WARNING,
    'flask': logging.WARNING,
    'apscheduler': logging.WARNING,
}

correlation_id: ContextVar[str | None] = ContextVar('correlation_id', default=None)


def bind_correlation_id(value: str | None = None) -> str:
    """Bind a correlation id to the current context, generating one when absent."""
    cid = value or uuid.uuid4().hex[:8]
    correlation_id.set(cid)
    return cid


def reset_correlation_id() -> None:
    """Clear the current context's correlation id."""
    correlation_id.set(None)


class CorrelationIdFilter(logging.Filter):
    """Copies the context correlation id onto every record it sees."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.cid = correlation_id.get()
        return True


class CorrelationIdFormatter(logging.Formatter):
    """Prefixes the message with ``[cid:...]`` and flattens newlines inside it.

    ``logging.Formatter.format`` appends the traceback after the message field, so the
    traceback keeps its own lines while the message itself cannot forge a new log entry.
    """

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage().replace('\r', ' ').replace('\n', ' ')
        if cid := getattr(record, 'cid', None):
            message = f'[cid:{cid}] {message}'
        plain = copy.copy(record)
        plain.msg, plain.args = message, ()
        return super().format(plain)


def _trim_log_file(path: Path, max_bytes: int) -> None:
    """Keep only the last ``max_bytes // 2`` bytes, starting at the first full line."""
    if not path.exists() or path.stat().st_size <= max_bytes:
        return

    # Every process calls create_app(); only the first one to take the lock trims.
    lock = path.with_name(f'{path.name}.trim.lock')
    try:
        os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
    except OSError:
        return
    # shortcut: a crash mid-trim leaves the lock file behind, so delete it by hand.
    try:
        keep = max_bytes // 2
        with path.open('rb') as f:
            f.seek(-keep, os.SEEK_END)
            tail = f.read()

        if (newline := tail.find(b'\n')) == -1:
            return  # a single line longer than the kept half: nothing safe to drop

        path.write_bytes(tail[newline + 1 :])
    finally:
        lock.unlink(missing_ok=True)


def configure_logging(app: Flask) -> None:
    """Send every logger to one file handler on the root logger and bind request ids."""
    log_path = Path(app.config['LOG_FILE'])
    log_path.parent.mkdir(parents=True, exist_ok=True)
    _trim_log_file(log_path, app.config['LOG_MAX_BYTES'])

    root = logging.getLogger()
    if not any(getattr(handler, 'pf_log_handler', False) for handler in root.handlers):
        handler = logging.FileHandler(log_path, mode='a', encoding='utf-8', delay=True)
        handler.setFormatter(CorrelationIdFormatter(LOG_FORMAT))
        handler.addFilter(CorrelationIdFilter())
        handler.pf_log_handler = True
        root.addHandler(handler)

    root.setLevel(app.config['LOG_LEVEL'])
    for name, level in QUIET_LOGGERS.items():
        logging.getLogger(name).setLevel(level)

    @app.before_request
    def _bind_request_correlation_id() -> None:
        bind_correlation_id()
