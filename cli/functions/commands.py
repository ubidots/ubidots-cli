import typer

from cli.functions.enums import FunctionLanguageEnum
from cli.functions.handlers import handler_function_new
from cli.functions.handlers import handler_function_pull
from cli.functions.handlers import handler_function_push
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
    handler_function_new(name=name, language=language)


@app.command(
    help="Update and synchronize your local function code with the remote server."
)
def push():
    handler_function_push()


@app.command(
    help="Retrieve and update your local function code with the latest changes from the remote server."
)
def pull():
    handler_function_pull()
