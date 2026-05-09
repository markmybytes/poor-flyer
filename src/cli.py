import subprocess
import sys

import click
from flask.cli import with_appcontext


def register_commands(app):

    @app.cli.command("dev")
    @with_appcontext
    def dev():
        """Run Vite watch and Flask server simultaneously."""
        click.echo(click.style("🚀 Starting development environment...", fg="cyan"))

        vitep = subprocess.Popen(
            ["npm", "run", "watch"],
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
