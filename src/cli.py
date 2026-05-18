import subprocess
import sys
import time
from pathlib import Path

import click
from flask import current_app
from flask.cli import with_appcontext

from src.services.scheduler import start_scheduler, stop_scheduler


def _terminate_process(proc: subprocess.Popen, label: str) -> None:
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        click.echo(click.style(f'Force stopping {label}...', fg='yellow'))
        proc.terminate()
        proc.wait(timeout=5)


@click.command(name='dev')
@with_appcontext
def dev():
    """Run Vite dev server, Flask dev server, and scheduler simultaneously."""
    click.echo(click.style('Starting development environment...', fg='cyan'))

    hot_file = Path(current_app.config['VITE_HOT_FILE'])
    hot_file.unlink(missing_ok=True)

    vite_process = subprocess.Popen(['npm', 'run', 'dev'], stdin=subprocess.DEVNULL)
    scheduler_process = subprocess.Popen(['flask', '--app', 'wsgi:app', 'run-scheduler'])

    try:
        subprocess.run(['flask', '--app', 'wsgi:app', 'run', '--debug'], check=True)
    except KeyboardInterrupt:
        click.echo(click.style('\nShutting down development services...', fg='yellow'))
    except subprocess.CalledProcessError as exc:
        click.echo(click.style(f'Error starting Flask dev server: {exc}', fg='red'))
    finally:
        for process, label in [(scheduler_process, 'scheduler'), (vite_process, 'vite')]:
            if process.poll() is None:
                process.terminate()
            _terminate_process(process, label)

        hot_file.unlink(missing_ok=True)
        sys.exit(0)


@click.command(name='run-scheduler')
@with_appcontext
def run_scheduler():
    """Run APScheduler as a dedicated long-lived process."""
    click.echo(click.style('Starting scheduler process...', fg='cyan'))

    start_scheduler()

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        click.echo(click.style('\nShutting down scheduler...', fg='yellow'))
    finally:
        stop_scheduler()
        click.echo(click.style('Scheduler stopped.', fg='green'))
