from typing import Annotated

import typer

from cli.commons.utils import verbose_option
from cli.functions import handlers
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.settings import engine_settings
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.enums import FunctionMethodEnum
from cli.functions.enums import FunctionRuntimeLayerTypeEnum
from cli.settings import settings

app = typer.Typer(help="Tool for managing and deploying functions.")


@app.command(help="Create a new local function.")
@verbose_option()
def new(
    name: Annotated[
        str, typer.Argument(help="The name of the project folder.")
    ] = settings.FUNCTIONS.DEFAULT_PROJECT_NAME,
    runtime: Annotated[
        FunctionRuntimeLayerTypeEnum,
        typer.Argument(
            help="The runtime for the function. **Required** if not in interactive mode.",
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
            help=(
                "Enable interactive mode to select language and runtime through prompts. "
                "If not set, 'runtime' is required."
            ),
        ),
    ] = False,
    verbose: bool = False,
):
    if interactive:
        language = FunctionLanguageEnum.choose(message="Select a programming language:")
        runtime = language.choose_runtime(message=f"Select a {language} runtime:")
    else:
        if not runtime:
            available_runtimes = [
                runtime.value for runtime in FunctionRuntimeLayerTypeEnum
            ]
            raise typer.BadParameter(
                param_hint="RUNTIME", message=", ".join(available_runtimes)
            )

        language = (
            FunctionLanguageEnum.PYTHON
            if runtime.value.startswith(FunctionLanguageEnum.PYTHON)
            else FunctionLanguageEnum.NODEJS
        )

    handlers.create_function(
        name=name,
        language=language,
        runtime=runtime,
        methods=FunctionMethodEnum.parse_methods_to_enum_list(methods),
        is_raw=raw,
        cron=cron,
        cors=cors,
        verbose=verbose,
    )


@app.command(help="Initialize the function container environment for execution.")
@verbose_option()
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
@verbose_option()
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
@verbose_option()
def status(
    engine: Annotated[
        FunctionEngineTypeEnum,
        typer.Option(help="The engine used to serve the function.", hidden=True),
    ] = engine_settings.CONTAINER.DEFAULT_ENGINE,
    verbose: bool = False,
):
    handlers.status_function(engine=engine, verbose=verbose)


@app.command(help="Get logs from the function.")
@verbose_option()
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
@verbose_option()
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
@verbose_option()
def pull(
    confirm: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Confirm file overwrite without prompt."),
    ] = False,
    verbose: bool = False,
):
    handlers.pull_function(confirm=confirm, verbose=verbose)
