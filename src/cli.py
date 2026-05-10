import subprocess
import sys

import click
from flask.cli import with_appcontext


@click.command(name="dev")
@with_appcontext
def dev():
    """Run Vite dev server and Flask server simultaneously.

    Simplified: assume Vite will use port 5173 and pass that to Flask.
    """
    click.echo(click.style("🚀 Starting development environment...", fg="cyan"))

    vitep = subprocess.Popen(
        ["npm", "run", "dev"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        subprocess.run(["flask", "run", "--debug"], check=True)
    except KeyboardInterrupt:
        click.echo(click.style("\nShutting down servers...", fg="yellow"))
    except subprocess.CalledProcessError as e:
        click.echo(click.style(f"Error starting Flask: {e}", fg="red"))
    finally:
        vitep.terminate()
        sys.exit(0)
