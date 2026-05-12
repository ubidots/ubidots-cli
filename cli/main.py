import typer

from cli.apps.commands import app as apps_app
from cli.auth.commands import login
from cli.auth.commands import logout
from cli.auth.commands import whoami
from cli.config.commands import config
from cli.devices.commands import app as device_app
from cli.functions.commands import app as function_app
from cli.pages.commands import app as page_app
from cli.variables.commands import app as variable_app

app = typer.Typer()

app.command(help="Configure general settings for the CLI.")(config)
app.command(help="Authenticate with Ubidots via OAuth2 (Authorization Code + PKCE).")(login)
app.command(help="Revoke the OAuth refresh token and clear the local session.")(logout)
app.command(help="Show the OAuth session details from the local JWT.")(whoami)
app.add_typer(function_app, name="functions")
app.add_typer(device_app, name="devices")
app.add_typer(variable_app, name="variables")
app.add_typer(page_app, name="pages")
app.add_typer(apps_app, name="apps")

if __name__ == "__main__":
    app()
