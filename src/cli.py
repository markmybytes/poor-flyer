import subprocess
import sys
from pathlib import Path

import click
from flask import current_app
from flask.cli import with_appcontext


@click.command(name="dev")
@with_appcontext
def dev():
    """Run Vite dev server and Flask server simultaneously."""
    click.echo(click.style("🚀 Starting development environment...", fg="cyan"))

    hot_file = Path(current_app.config["VITE_HOT_FILE"])
    hot_file.unlink(missing_ok=True)

    vitep = subprocess.Popen(
        ["npm", "run", "dev"],
        stdin=subprocess.DEVNULL,  # block Vite from touching stdin to protect the terminal
    )

    try:
        subprocess.run(["flask", "run", "--debug"], check=True)
    except KeyboardInterrupt:
        click.echo(click.style("\nShutting down servers...", fg="yellow"))
    except subprocess.CalledProcessError as e:
        click.echo(click.style(f"Error starting Flask: {e}", fg="red"))
    finally:
        try:
            vitep.wait(timeout=3)
        except subprocess.TimeoutExpired:
            vitep.terminate()  # forcefully terminate if it gets stuck
            vitep.wait()

        hot_file.unlink(missing_ok=True)
        sys.exit(0)
