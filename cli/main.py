import typer

from cli.config.commands import config
from cli.devices.commands import app as device_app
from cli.functions.commands import app as function_app
from cli.pages.commands import app as pages_app
from cli.variables.commands import app as variable_app

app = typer.Typer()

app.command(help="Configure general settings for the CLI.")(config)
app.add_typer(function_app, name="functions")
app.add_typer(device_app, name="devices")
app.add_typer(variable_app, name="variables")
app.add_typer(pages_app, name="pages")

if __name__ == "__main__":
    app()
