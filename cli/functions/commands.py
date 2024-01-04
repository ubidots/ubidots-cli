import typer

from cli.functions import handlers
from cli.functions.enums import FunctionLanguageEnum
from cli.settings import settings

app = typer.Typer(help="Tool for managing and deploying functions via API.")


@app.command(help="Create a new local function.")
def new(
    name: str = typer.Argument(
        default=settings.FUNCTIONS.DEFAULT_PROJECT_NAME,
        help="The name of the project folder.",
    )
):
    language = FunctionLanguageEnum.choose(message="Select a programming language:")
    handlers.create_function(name=name, language=language)


@app.command(
    help="Update and synchronize your local function code with the remote server."
)
def push():
    handlers.push_function()


@app.command(
    help="Retrieve and update your local function code with the latest changes from the remote server."
)
def pull():
    handlers.pull_function()
