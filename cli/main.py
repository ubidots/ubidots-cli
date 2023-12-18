import typer

from cli.config.commands import config
from cli.functions.commands import app as function_app

app = typer.Typer()

app.command(help="Configure general settings for the CLI.")(config)

app.add_typer(function_app, name="fn")

if __name__ == "__main__":
    app()
