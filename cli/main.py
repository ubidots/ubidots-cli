import typer

from cli.apps.commands import app as apps_app
from cli.commons.machine_help import install_machine_help_patch
from cli.config.commands import config
from cli.devices.commands import app as device_app
from cli.functions.commands import app as function_app
from cli.pages.commands import app as page_app
from cli.variables.commands import app as variable_app

install_machine_help_patch()

app = typer.Typer()

app.command(help="Configure general settings for the CLI.")(config)
app.add_typer(function_app, name="functions")
app.add_typer(device_app, name="devices")
app.add_typer(variable_app, name="variables")
app.add_typer(page_app, name="pages")
app.add_typer(apps_app, name="apps")

if __name__ == "__main__":
    app()
