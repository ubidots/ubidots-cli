from typing import Annotated

import typer

from cli.functions import handlers
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.settings import engine_settings
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
    runtime = language.choose_runtime(message=f"Select a {language} runtime:")
    handlers.create_function(name=name, language=language, runtime=runtime)


@app.command(help="Initialize the function container environment for execution.")
def start(
    engine: Annotated[
        FunctionEngineTypeEnum,
        typer.Option(help="The engine used to serve the function.", show_default=False),
    ] = FunctionEngineTypeEnum.DOCKER,
    port: Annotated[
        int,
        typer.Option(help="The host port to bind the function."),
    ] = engine_settings.CONTAINER.FRIE.EXTERNAL_PORT,
    raw: Annotated[
        bool,
        typer.Option(help="Flag to determine if the output should be in raw format."),
    ] = False,
    method: Annotated[
        FunctionMethodEnum,
        typer.Option(help="The HTTP method the function will respond to."),
    ] = FunctionMethodEnum.GET,
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
        port=port,
        raw=raw,
        method=method,
        token=token,
        cors=cors,
        cron=cron,
        timeout=timeout,
    )


@app.command(help="Stop the function.")
def stop(
    label: Annotated[
        str, typer.Argument(help="The label of function.", show_default=False)
    ],
    engine: Annotated[
        FunctionEngineTypeEnum,
        typer.Option(help="The engine used to serve the function."),
    ] = FunctionEngineTypeEnum.DOCKER,
):
    handlers.stop_function(engine=engine, label=label)


@app.command(help="Check the status of the functions.")
def status(
    engine: Annotated[
        FunctionEngineTypeEnum,
        typer.Option(help="The engine used to serve the function."),
    ] = FunctionEngineTypeEnum.DOCKER,
):
    handlers.status_function(engine=engine)


@app.command(help="Get logs from the function.")
def logs(
    label: Annotated[
        str, typer.Argument(help="The label of function.", show_default=False)
    ],
    engine: Annotated[
        FunctionEngineTypeEnum,
        typer.Option(help="The engine used to serve the function."),
    ] = FunctionEngineTypeEnum.DOCKER,
    tail: Annotated[
        str,
        typer.Option(
            "--tail/",
            "-n/",
            help="Output specified number of lines at the end of logs.",
        ),
    ] = "all",
    follow: Annotated[
        bool,
        typer.Option("--follow/", "-f/", help="Follow log output."),
    ] = False,
):
    handlers.logs_function(engine=engine, label=label, tail=tail, follow=follow)


@app.command(help="Test the lambda function locally in a Docker container environment.")
def run(
    engine: Annotated[
        FunctionEngineTypeEnum,
        typer.Option(help="The engine used to serve the function."),
    ] = FunctionEngineTypeEnum.DOCKER,
    payload: Annotated[
        str,
        typer.Option(
            help='Payload as JSON string for function testing. e.g. \'{"key": "value"}\'',
            show_default=False,
        ),
    ] = "{}",
):
    handlers.run_function(engine=engine, payload=payload)


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
