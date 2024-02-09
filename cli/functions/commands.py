from typing import Annotated

import typer

from cli.functions import handlers
from cli.functions.enums import FunctionLanguageEnum
from cli.settings import settings

app = typer.Typer(help="Tool for managing and deploying functions via API.")


@app.command(help="Create a new local function.")
def new(
    name: Annotated[
        str, typer.Argument(help="The name of the project folder.")
    ] = settings.FUNCTIONS.DEFAULT_PROJECT_NAME
):
    language = FunctionLanguageEnum.choose(message="Select a programming language:")
    runtime = language.choose_runtime(message=f"Select a {language.value} runtime:")
    handlers.create_function(name=name, language=language, runtime=runtime)


@app.command(help="Initialize the function container environment for execution.")
def init(
    host_port: Annotated[
        int, typer.Option(help="host port to bind the container.")
    ] = settings.FUNCTIONS.DOCKER_CONFIG.HOST_PORT
):
    handlers.init_function(host_port=host_port)


@app.command(help="Test the lambda function locally in a Docker container environment.")
def test(
    host_port: Annotated[
        int, typer.Option(help="host port to bind the container.")
    ] = settings.FUNCTIONS.DOCKER_CONFIG.HOST_PORT,
    payload: Annotated[
        str,
        typer.Option(
            help='Payload as JSON string for function testing. e.g. \'{"key": "value"}\'',
            show_default=False,
        ),
    ] = "{}",
):
    handlers.test_function(host_port=host_port, payload=payload)


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
