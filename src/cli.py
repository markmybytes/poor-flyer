import subprocess
import sys
import threading
from pathlib import Path

import click
from flask import current_app
from flask.cli import with_appcontext

from src.extensions.scheduler import start_scheduler, stop_scheduler


def _terminate_process(proc: subprocess.Popen, label: str) -> None:
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        click.echo(click.style(f'Force stopping {label}...', fg='yellow'))
        proc.terminate()
        proc.wait(timeout=5)


def _stream_prefixed_output(proc: subprocess.Popen, label: str, color: str | None = None) -> None:
    if proc.stdout is None:
        return

    for line in proc.stdout:
        message = line.rstrip()
        if message:
            click.echo(click.style(f'[{label}] {message}', fg=color))


@click.command(name='dev')
@with_appcontext
def dev():
    """Run Vite dev server, Flask dev server, and scheduler simultaneously."""
    click.echo(click.style('Starting development environment...', fg='cyan'))

    hot_file = Path(current_app.config['VITE_HOT_FILE'])
    hot_file.unlink(missing_ok=True)

    flask_cmd = [sys.executable, '-m', 'flask', '--app', 'wsgi:app']

    process_specs = [
        ('vite', ['npm', 'run', 'dev'], None),
        ('scheduler', [*flask_cmd, 'run-scheduler'], 'blue'),
        ('server', [*flask_cmd, 'run', '--debug'], None),
    ]

    processes: dict[str, subprocess.Popen] = {}
    stream_threads: list[threading.Thread] = []

    for label, command, color in process_specs:
        proc = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1,
        )
        processes[label] = proc

        thread = threading.Thread(
            target=_stream_prefixed_output,
            args=(proc, label, color),
            daemon=True,
        )
        thread.start()
        stream_threads.append(thread)

    try:
        server_exit_code = processes['server'].wait()
        if server_exit_code != 0:
            raise subprocess.CalledProcessError(server_exit_code, processes['server'].args)
    except KeyboardInterrupt:
        click.echo(click.style('\nShutting down development services...', fg='yellow'))
    except subprocess.CalledProcessError as exc:
        click.echo(click.style(f'Error starting Flask dev server: {exc}', fg='red'))
    finally:
        for label, process in processes.items():
            if process.poll() is None:
                process.terminate()
            _terminate_process(process, label)

        for thread in stream_threads:
            thread.join(timeout=1)

        hot_file.unlink(missing_ok=True)
        sys.exit(0)


@click.command(name='run-scheduler')
@with_appcontext
def run_scheduler():
    """Run APScheduler as a dedicated long-lived process."""
    click.echo(click.style('Starting scheduler process...', fg='cyan'))

    try:
        start_scheduler()
    except KeyboardInterrupt:
        click.echo(click.style('\nShutting down scheduler...', fg='yellow'))
    finally:
        stop_scheduler()
        click.echo(click.style('Scheduler stopped.', fg='green'))
