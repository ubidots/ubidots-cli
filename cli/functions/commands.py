from typing import Annotated

import typer

from cli.functions import handlers
from cli.functions.engines.enums import FunctionEngineServeEnum
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.enums import FunctionMethodEnum
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
def start(
    engine: Annotated[
        FunctionEngineServeEnum,
        typer.Option(help="The engine used to serve the function."),
    ] = FunctionEngineServeEnum.DOCKER.value,
    host: Annotated[
        str,
        typer.Option(
            help="The hostname or IP address for the function container to bind to."
        ),
    ] = settings.FUNCTIONS.DOCKER_CONFIG.HOST,
    port: Annotated[
        int,
        typer.Option(
            help="The host port to bind the function container to for network access."
        ),
    ] = settings.FUNCTIONS.DOCKER_CONFIG.PORT,
    raw: Annotated[
        bool,
        typer.Option(help="Flag to determine if the output should be in raw format."),
    ] = False,
    method: Annotated[
        FunctionMethodEnum,
        typer.Option(help="The HTTP method the function will respond to."),
    ] = FunctionMethodEnum.GET.value,
    token: Annotated[
        str, typer.Option(help="Optional authentication token to invoke the function.")
    ] = "",
    cors: Annotated[
        bool,
        typer.Option(
            help="Flag to enable Cross-Origin Resource Sharing (CORS) for the function."
        ),
    ] = False,
    cron: Annotated[
        str,
        typer.Option(
            help="Cron expression to schedule the function for periodic execution."
        ),
    ] = settings.FUNCTIONS.DEFAULT_CRON,
    timeout: Annotated[
        int,
        typer.Option(
            help="Maximum time (in seconds) the function is allowed to run before being terminated."
        ),
    ] = settings.FUNCTIONS.MAX_TIMEOUT_SECONDS,
):
    handlers.start_function(
        engine=engine,
        host=host,
        port=port,
        raw=raw,
        method=method,
        token=token,
        cors=cors,
        cron=cron,
        timeout=timeout,
    )


@app.command(help="Test the lambda function locally in a Docker container environment.")
def run(
    port: Annotated[
        int, typer.Option(help="host port to bind the container.")
    ] = settings.FUNCTIONS.DOCKER_CONFIG.PORT,
    payload: Annotated[
        str,
        typer.Option(
            help='Payload as JSON string for function testing. e.g. \'{"key": "value"}\'',
            show_default=False,
        ),
    ] = "{}",
):
    handlers.run_function(host_port=port, payload=payload)


@app.command(
    help="Update and synchronize your local function code with the remote server."
)
def push(
    confirm: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Confirm file overwrite without prompt."),
    ] = False
):
    handlers.push_function(confirm=confirm)


@app.command(
    help="Retrieve and update your local function code with the latest changes from the remote server."
)
def pull(
    confirm: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Confirm file overwrite without prompt."),
    ] = False
):
    handlers.pull_function(confirm=confirm)
