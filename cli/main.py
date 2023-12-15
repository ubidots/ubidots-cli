import typer

from cli.config.commands import app as config_app
from cli.functions.commands import app as fn_app

app = typer.Typer()

app.add_typer(config_app, name="config")
app.add_typer(fn_app, name="fn")

if __name__ == "__main__":
    app()
