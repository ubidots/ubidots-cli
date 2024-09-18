from typing import Annotated

import typer
from InquirerPy import inquirer

from cli.commons.decorators import add_verbose_option
from cli.functions import handlers
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.settings import engine_settings
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.enums import FunctionMethodEnum
from cli.functions.enums import FunctionNodejsRuntimeLayerTypeEnum
from cli.functions.enums import FunctionPythonRuntimeLayerTypeEnum
from cli.functions.enums import FunctionRuntimeLayerTypeEnum
from cli.settings import settings

app = typer.Typer(help="Tool for managing and deploying functions.")


@app.command(help="Create a new local function.")
@add_verbose_option()
def new(
    name: Annotated[
        str, typer.Argument(help="The name of the project folder.")
    ] = settings.FUNCTIONS.DEFAULT_PROJECT_NAME,
    runtime: Annotated[
        FunctionRuntimeLayerTypeEnum,
        typer.Argument(
            help="The runtime for the function.",
        ),
    ] = FunctionRuntimeLayerTypeEnum.NODEJS_20_LITE,
    cors: Annotated[
        bool,
        typer.Option(
            help="Flag to enable Cross-Origin Resource Sharing (CORS) for the function.",
        ),
    ] = False,
    cron: Annotated[
        str,
        typer.Option(
            help="Cron expression to schedule the function for periodic execution."
        ),
    ] = settings.FUNCTIONS.DEFAULT_CRON,
    methods: Annotated[
        str,
        typer.Option(help="The HTTP methods the function will respond to."),
    ] = FunctionMethodEnum.default(),
    raw: Annotated[
        bool,
        typer.Option(help="Flag to determine if the output should be in raw format."),
    ] = False,
    interactive: Annotated[
        bool,
        typer.Option(
            "--interactive",
            "-i",
            help=("Enable interactive mode to select some options through prompts. "),
        ),
    ] = False,
    verbose: bool = False,
):
    if interactive:
        selected_name: str = inquirer.text(
            message="Enter the name of the project:",
            default=settings.FUNCTIONS.DEFAULT_PROJECT_NAME,
        ).execute()
        selected_language: FunctionLanguageEnum = inquirer.select(
            message="Select a programming language:",
            choices=list(FunctionLanguageEnum),
        ).execute()
        selected_runtime: (
            FunctionRuntimeLayerTypeEnum
            | FunctionPythonRuntimeLayerTypeEnum
            | FunctionNodejsRuntimeLayerTypeEnum
        ) = inquirer.select(
            message="Select a programming a runtime:",
            choices=list(selected_language.runtime),
        ).execute()
        selected_methods: list[FunctionMethodEnum] = inquirer.checkbox(
            message="Pick the HTTP methods:",
            choices=list(FunctionMethodEnum),
            instruction="(select at least 1)",
            validate=lambda selection: len(selection) >= 1,
        ).execute()
        selected_cron: str = inquirer.text(
            message="Enter a cron:",
            default=settings.FUNCTIONS.DEFAULT_CRON,
        ).execute()
        selected_raw: bool = inquirer.confirm(
            message="Enable?", default=False
        ).execute()
        selected_cors: bool = inquirer.confirm(
            message="Enable?", default=False
        ).execute()
    else:
        selected_name = name
        selected_runtime = runtime
        selected_language = FunctionLanguageEnum.get_language_by_runtime(runtime)
        selected_methods = FunctionMethodEnum.parse_methods_to_enum_list(methods)
        selected_cron = cron
        selected_raw = raw
        selected_cors = cors

    handlers.create_function(
        name=selected_name,
        language=selected_language,
        runtime=selected_runtime,
        methods=selected_methods,
        is_raw=selected_raw,
        cron=selected_cron,
        cors=selected_cors,
        verbose=verbose,
    )


@app.command(help="Initialize the function container environment for execution.")
@add_verbose_option()
def start(
    engine: Annotated[
        FunctionEngineTypeEnum,
        typer.Option(help="The engine used to serve the function.", hidden=True),
    ] = engine_settings.CONTAINER.DEFAULT_ENGINE,
    cors: Annotated[
        bool,
        typer.Option(
            help="Flag to enable Cross-Origin Resource Sharing (CORS) for the function.",
        ),
    ] = False,
    cron: Annotated[
        str,
        typer.Option(
            help="Cron expression to schedule the function for periodic execution."
        ),
    ] = settings.FUNCTIONS.DEFAULT_CRON,
    methods: Annotated[
        str,
        typer.Option(help="The HTTP methods the function will respond to."),
    ] = FunctionMethodEnum.default(),
    raw: Annotated[
        bool,
        typer.Option(help="Flag to determine if the output should be in raw format."),
    ] = False,
    timeout: Annotated[
        int,
        typer.Option(
            help=(
                "Maximum time (in seconds) the function is allowed to run before being terminated. "
                f"[max: {settings.FUNCTIONS.MAX_TIMEOUT_SECONDS}]"
            )
        ),
    ] = settings.FUNCTIONS.DEFAULT_TIMEOUT_SECONDS,
    token: Annotated[
        str, typer.Option(help="Optional authentication token to invoke the function.")
    ] = "",
    verbose: bool = False,
):
    handlers.start_function(
        engine=engine,
        methods=FunctionMethodEnum.parse_methods_to_enum_list(methods),
        is_raw=raw,
        token=token,
        cors=cors,
        cron=cron,
        timeout=timeout,
        verbose=verbose,
    )


@app.command(help="Stop the function.")
@add_verbose_option()
def stop(
    label: Annotated[
        str,
        typer.Argument(help="The label of the function.", show_default=False),
    ],
    engine: Annotated[
        FunctionEngineTypeEnum,
        typer.Option(help="The engine used to serve the function.", hidden=True),
    ] = engine_settings.CONTAINER.DEFAULT_ENGINE,
    verbose: bool = False,
):
    handlers.stop_function(engine=engine, label=label, verbose=verbose)


@app.command(help="Check the status of the functions.")
@add_verbose_option()
def status(
    engine: Annotated[
        FunctionEngineTypeEnum,
        typer.Option(help="The engine used to serve the function.", hidden=True),
    ] = engine_settings.CONTAINER.DEFAULT_ENGINE,
    verbose: bool = False,
):
    handlers.status_function(engine=engine, verbose=verbose)


@app.command(help="Get logs from the function.")
@add_verbose_option()
def logs(
    label: Annotated[
        str, typer.Argument(help="The label of function.", show_default=False)
    ],
    engine: Annotated[
        FunctionEngineTypeEnum,
        typer.Option(help="The engine used to serve the function.", hidden=True),
    ] = engine_settings.CONTAINER.DEFAULT_ENGINE,
    follow: Annotated[
        bool,
        typer.Option("--follow/", "-f/", help="Follow log output."),
    ] = False,
    remote: Annotated[
        bool,
        typer.Option("--remote/", "-r/", help="Fetch logs from the remote server."),
    ] = False,
    tail: Annotated[
        str,
        typer.Option(
            "--tail/",
            "-n/",
            help="Output specified number of lines at the end of logs.",
        ),
    ] = "all",
    verbose: bool = False,
):
    handlers.logs_function(
        engine=engine,
        label=label,
        tail=tail,
        follow=follow,
        remote=remote,
        verbose=verbose,
    )


@app.command(
    help="Update and synchronize your local function code with the remote server."
)
@add_verbose_option()
def push(
    confirm: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Confirm file overwrite without prompt."),
    ] = False,
    verbose: bool = False,
):
    handlers.push_function(confirm=confirm, verbose=verbose)


@app.command(
    help="Retrieve and update your local function code with the latest changes from the remote server."
)
@add_verbose_option()
def pull(
    confirm: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Confirm file overwrite without prompt."),
    ] = False,
    verbose: bool = False,
):
    handlers.pull_function(confirm=confirm, verbose=verbose)
