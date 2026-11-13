import contextvars
import logging
import threading

import pytest

from src.logging_config import (
    LOG_FORMAT,
    QUIET_LOGGERS,
    bind_correlation_id,
    configure_logging,
    correlation_id,
    reset_correlation_id,
)
from src.services.scheduler import disable_departured_itineraries, scrape_fares


@pytest.fixture
def isolated_root(app):
    """Detach the handlers this app attached so each test configures a fresh root logger."""
    root = logging.getLogger()
    saved_handlers = root.handlers[:]
    saved_level = root.level
    saved_hooks = {key: funcs[:] for key, funcs in app.before_request_funcs.items()}
    saved_first_request = app._got_first_request

    # configure_logging registers a hook, which Flask refuses after the first test request.
    app._got_first_request = False
    root.handlers[:] = [h for h in saved_handlers if not getattr(h, 'pf_log_handler', False)]

    yield root

    for handler in root.handlers:
        if handler not in saved_handlers:
            handler.close()
    root.handlers[:] = saved_handlers
    root.setLevel(saved_level)
    app.before_request_funcs.clear()
    app.before_request_funcs.update(saved_hooks)
    app._got_first_request = saved_first_request


@pytest.fixture
def configured_log(app, tmp_path, isolated_root):
    log_path = tmp_path / 'app.log'
    saved = {key: app.config[key] for key in ('LOG_FILE', 'LOG_MAX_BYTES', 'LOG_LEVEL')}
    app.config.update(LOG_FILE=str(log_path), LOG_MAX_BYTES=200, LOG_LEVEL='DEBUG')

    configure_logging(app)

    yield log_path

    app.config.update(saved)


def _app_handlers(root: logging.Logger, log_path) -> list[logging.FileHandler]:
    return [
        h
        for h in root.handlers
        if isinstance(h, logging.FileHandler) and h.baseFilename == str(log_path.resolve())
    ]


def test_one_file_handler_on_root_with_lazy_open(configured_log, isolated_root):
    handlers = _app_handlers(isolated_root, configured_log)
    assert len(handlers) == 1

    handler = handlers[0]
    assert handler.mode == 'a'
    assert handler.encoding == 'utf-8'
    assert handler.delay is True
    assert handler.formatter._fmt == LOG_FORMAT


def test_configure_logging_is_idempotent(configured_log, isolated_root, app):
    configure_logging(app)
    configure_logging(app)

    assert len(_app_handlers(isolated_root, configured_log)) == 1


def test_root_level_and_quiet_loggers(configured_log, isolated_root, app):
    assert isolated_root.level == logging.DEBUG
    assert logging.getLogger('src').level == logging.NOTSET
    for name, level in QUIET_LOGGERS.items():
        assert logging.getLogger(name).level == level


def test_third_party_record_reaches_the_file(configured_log):
    logging.getLogger('sqlalchemy.engine').warning('third party says hello')

    assert 'third party says hello' in configured_log.read_text(encoding='utf-8')


def test_record_gets_correlation_id_and_prefix(configured_log):
    cid = bind_correlation_id()
    logging.getLogger('src.demo').info('scrape finished')

    line = configured_log.read_text(encoding='utf-8').strip()
    assert f' - src.demo - [cid:{cid}] scrape finished' in line


def test_bind_correlation_id_generates_eight_hex_chars():
    cid = bind_correlation_id()
    try:
        assert len(cid) == 8
        assert int(cid, 16) >= 0
        assert correlation_id.get() == cid
    finally:
        reset_correlation_id()


def test_reset_correlation_id_clears_the_context():
    bind_correlation_id('abc12345')
    reset_correlation_id()

    assert correlation_id.get() is None


def test_request_binds_a_correlation_id(app, isolated_root):
    reset_correlation_id()

    with app.test_request_context('/'):
        app.preprocess_request()
        assert correlation_id.get() is not None

    reset_correlation_id()


def test_newline_in_message_cannot_forge_a_log_entry(configured_log):
    bind_correlation_id('deadbeef')
    logging.getLogger('src.demo').error('first line\n2024-01-01 00:00:00,000 - ERROR - x - forged')

    lines = configured_log.read_text(encoding='utf-8').splitlines()
    assert len(lines) == 1
    assert lines[0].endswith('first line 2024-01-01 00:00:00,000 - ERROR - x - forged')
    reset_correlation_id()


def test_traceback_stays_multi_line(configured_log):
    try:
        raise ValueError('boom')
    except ValueError:
        logging.getLogger('src.demo').exception('request failed')

    lines = configured_log.read_text(encoding='utf-8').splitlines()
    assert lines[0].endswith('request failed')
    assert len(lines) > 1
    assert 'ValueError: boom' in lines[-1]


def test_oversized_log_is_trimmed_to_last_half_on_line_boundary(app, tmp_path, isolated_root):
    log_path = tmp_path / 'big.log'
    lines = [f'line-{index:03d}-' + 'x' * 30 for index in range(50)]
    log_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    app.config.update(LOG_FILE=str(log_path), LOG_MAX_BYTES=400)
    configure_logging(app)

    kept = log_path.read_text(encoding='utf-8').splitlines()
    assert kept == lines[-len(kept) :]
    assert log_path.stat().st_size <= 200


def test_small_log_is_left_untouched(app, tmp_path, isolated_root):
    log_path = tmp_path / 'small.log'
    log_path.write_text('one\n', encoding='utf-8')

    app.config.update(LOG_FILE=str(log_path), LOG_MAX_BYTES=200)
    configure_logging(app)

    assert log_path.read_text(encoding='utf-8') == 'one\n'


def test_trim_is_skipped_when_another_process_holds_the_lock(app, tmp_path, isolated_root):
    log_path = tmp_path / 'busy.log'
    original = '\n'.join(f'line-{index:03d}-' + 'x' * 30 for index in range(50)) + '\n'
    log_path.write_text(original, encoding='utf-8')
    lock = log_path.with_name('busy.log.trim.lock')
    lock.write_text('', encoding='utf-8')

    app.config.update(LOG_FILE=str(log_path), LOG_MAX_BYTES=400)
    configure_logging(app)

    assert log_path.read_text(encoding='utf-8') == original
    assert lock.exists()


def test_correlation_id_survives_a_worker_thread(configured_log):
    bind_correlation_id('threaded')
    thread = threading.Thread(
        target=contextvars.copy_context().run,
        args=(logging.getLogger('src.demo').info, 'sent from a thread'),
    )
    thread.start()
    thread.join()

    assert '[cid:threaded] sent from a thread' in configured_log.read_text(encoding='utf-8')


def test_disable_job_binds_and_resets_correlation_id(mocker):
    seen: list[str | None] = []
    mocker.patch(
        'src.services.scheduler.setting.get_bool',
        side_effect=lambda *args, **kwargs: seen.append(correlation_id.get()) or False,
    )

    disable_departured_itineraries()

    assert seen[0] is not None
    assert correlation_id.get() is None


def test_scrape_job_binds_and_resets_correlation_id(app, mocker):
    seen: list[str | None] = []

    def record_and_fail() -> str:
        seen.append(correlation_id.get())
        raise RuntimeError('no fares today')

    mocker.patch('src.services.scheduler.get_configured_base_currency', side_effect=record_and_fail)

    with app.app_context():
        scrape_fares()

    assert seen[0] is not None
    assert correlation_id.get() is None
