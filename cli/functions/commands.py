from builtins import list as BuiltinList
from typing import Annotated
from typing import no_type_check

import typer
from InquirerPy import inquirer

from cli.commons.decorators import add_filter_option
from cli.commons.decorators import add_pagination_options
from cli.commons.decorators import add_sort_by_option
from cli.commons.decorators import add_verbose_option
from cli.commons.decorators import simple_lookup_key
from cli.commons.enums import DefaultInstanceFieldEnum
from cli.commons.enums import EntityNameEnum
from cli.commons.enums import OutputFormatFieldsEnum
from cli.commons.utils import get_instance_key
from cli.commons.validators import is_valid_json_string
from cli.functions import executor
from cli.functions import handlers
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.settings import engine_settings
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.enums import FunctionMethodEnum
from cli.functions.enums import FunctionNodejsRuntimeLayerTypeEnum
from cli.functions.enums import FunctionPythonRuntimeLayerTypeEnum
from cli.functions.enums import FunctionRuntimeLayerTypeEnum
from cli.settings import settings

FIELDS_FUNCTION_HELP_TEXT = (
    "Comma-separated fields to process * e.g. field1,field2,field3. "
    "* Available fields: (url, id, label, name, isActive, createdAt, serverless, "
    "triggers, environment, zipFileProperties)."
)
DEFAULT_METHODS = FunctionMethodEnum.get_default_method()

app = typer.Typer(help="Tool for managing and deploying functions.")


@app.command(help="Create a new local function.", hidden=True)
@add_verbose_option()
def new(
    name: Annotated[
        str, typer.Option(help="The name of the project folder.")
    ] = settings.FUNCTIONS.DEFAULT_PROJECT_NAME,
    runtime: Annotated[
        FunctionRuntimeLayerTypeEnum,
        typer.Option(
            help="The runtime for the function.",
        ),
    ] = FunctionRuntimeLayerTypeEnum.NODEJS_20_LITE,
    cors: Annotated[
        bool,
        typer.Option(
            help="Flag to enable Cross-Origin Resource Sharing (CORS) for the function.",
        ),
    ] = settings.FUNCTIONS.DEFAULT_HAS_CORS,
    cron: Annotated[
        str,
        typer.Option(
            help="Cron expression to schedule the function for periodic execution.",
            hidden=True,
        ),
    ] = settings.FUNCTIONS.DEFAULT_CRON,
    methods: Annotated[
        str,
        typer.Option(help="The HTTP methods the function will respond to."),
    ] = FunctionMethodEnum.get_default_method(),
    raw: Annotated[
        bool,
        typer.Option(help="Flag to determine if the output should be in raw format."),
    ] = settings.FUNCTIONS.DEFAULT_IS_RAW,
    interactive: Annotated[
        bool,
        typer.Option(
            "--interactive",
            "-i",
            help=("Enable interactive mode to select options through prompts."),
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
            choices=BuiltinList(FunctionLanguageEnum),
        ).execute()
        selected_runtime: (
            FunctionRuntimeLayerTypeEnum
            | FunctionPythonRuntimeLayerTypeEnum
            | FunctionNodejsRuntimeLayerTypeEnum
        ) = inquirer.select(
            message="Select a runtime:",
            choices=BuiltinList(selected_language.runtime),
        ).execute()
        selected_methods: BuiltinList[FunctionMethodEnum] = inquirer.checkbox(
            message="Pick the HTTP methods:",
            choices=BuiltinList(FunctionMethodEnum),
            instruction="(select at least 1)",
            validate=lambda selection: len(selection) >= 1,
        ).execute()
        selected_cron = settings.FUNCTIONS.DEFAULT_CRON
        #  TODO: Temporarily hidden while deciding on development approach
        # selected_cron: str = inquirer.text(
        #     message="Enter a cron:",
        #     default=settings.FUNCTIONS.DEFAULT_CRON,
        # ).execute()
        selected_raw: bool = inquirer.confirm(
            message="Do you want to enable raw output mode?",
            default=settings.FUNCTIONS.DEFAULT_IS_RAW,
        ).execute()
        selected_cors: bool = inquirer.confirm(
            message="Do you want to enable Cross-Origin Resource Sharing (CORS)",
            default=settings.FUNCTIONS.DEFAULT_HAS_CORS,
        ).execute()
    else:
        selected_name = name
        selected_runtime = runtime
        selected_language = FunctionLanguageEnum.get_language_by_runtime(runtime)
        selected_methods = FunctionMethodEnum.parse_methods_to_enum_list(methods)
        selected_cron = cron
        selected_raw = raw
        selected_cors = cors

    executor.create_function(
        name=selected_name,
        language=selected_language,
        runtime=selected_runtime,
        methods=selected_methods,
        is_raw=selected_raw,
        cron=selected_cron,
        cors=selected_cors,
        verbose=verbose,
    )


@app.command(
    help="Initialize the function container environment for execution.",
)
@add_verbose_option()
def start(
    engine: Annotated[
        FunctionEngineTypeEnum,
        typer.Option(help="The engine used to serve the function.", hidden=True),
    ] = engine_settings.CONTAINER.DEFAULT_ENGINE,
    cors: Annotated[
        bool,  # noqa: RUF013
        typer.Option(
            help="Flag to enable Cross-Origin Resource Sharing (CORS) for the function.",
        ),
    ] = None,  # type: ignore
    cron: Annotated[
        str,
        typer.Option(
            help="Cron expression to schedule the function for periodic execution.",
            hidden=True,
        ),
    ] = settings.FUNCTIONS.DEFAULT_CRON,
    methods: Annotated[
        str,
        typer.Option(help="The HTTP methods the function will respond to."),
    ] = DEFAULT_METHODS,
    raw: Annotated[
        bool,  # noqa: RUF013
        typer.Option(help="Flag to determine if the output should be in raw format."),
    ] = None,  # type: ignore
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
    parse_methods = (
        None
        if methods is DEFAULT_METHODS
        else FunctionMethodEnum.parse_methods_to_enum_list(methods)
    )
    executor.start_function(
        engine=engine,
        methods=parse_methods,
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
        typer.Option(help="The label of the function.", show_default=False),
    ] = "",
    engine: Annotated[
        FunctionEngineTypeEnum,
        typer.Option(help="The engine used to serve the function.", hidden=True),
    ] = engine_settings.CONTAINER.DEFAULT_ENGINE,
    verbose: bool = False,
):
    executor.stop_function(
        engine=engine,
        label=label,
        verbose=verbose,
    )


@app.command(help="Restart the function.")
@add_verbose_option()
def restart(
    engine: Annotated[
        FunctionEngineTypeEnum,
        typer.Option(help="The engine used to serve the function.", hidden=True),
    ] = engine_settings.CONTAINER.DEFAULT_ENGINE,
    verbose: bool = False,
):
    executor.restart_function(
        engine=engine,
        verbose=verbose,
    )


@app.command(help="Check the status of the functions.")
@add_verbose_option()
def status(
    engine: Annotated[
        FunctionEngineTypeEnum,
        typer.Option(help="The engine used to serve the function.", hidden=True),
    ] = engine_settings.CONTAINER.DEFAULT_ENGINE,
    verbose: bool = False,
):
    executor.status_function(
        engine=engine,
        verbose=verbose,
    )


@app.command(help="Get logs from the function.", hidden=True)
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
    executor.logs_function(
        engine=engine,
        label=label,
        tail=tail,
        follow=follow,
        remote=remote,
        verbose=verbose,
    )


@app.command(
    help="Update and synchronize your local function code with the remote server.",
)
@add_verbose_option()
def push(
    confirm: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Confirm file overwrite without prompt."),
    ] = False,
    verbose: bool = False,
):
    executor.push_function(
        confirm=confirm,
        verbose=verbose,
    )


@app.command(
    help="Retrieve and update your local function code with the latest changes from the remote server.",
)
@add_verbose_option()
def pull(
    confirm: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Confirm file overwrite without prompt."),
    ] = False,
    verbose: bool = False,
):
    executor.pull_function(
        confirm=confirm,
        verbose=verbose,
    )


@app.command(
    help="Clean up functions environment to ensure a fresh start.", hidden=True
)
@add_verbose_option()
def clean(
    engine: Annotated[
        FunctionEngineTypeEnum,
        typer.Option(help="The engine used to serve the function.", hidden=True),
    ] = engine_settings.CONTAINER.DEFAULT_ENGINE,
    confirm: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Confirm file overwrite without prompt."),
    ] = False,
    verbose: bool = False,
):
    executor.clean_functions(
        engine=engine,
        confirm=confirm,
        verbose=verbose,
    )


@app.command(short_help="Deletes a specific function using its id or label.")
@simple_lookup_key(entity_name=EntityNameEnum.FUNCTION)
def delete(id: str | None = None, label: str | None = None):
    function_key = get_instance_key(id=id, label=label)

    handlers.delete_function(
        function_key=function_key,
    )


@app.command(short_help="Retrieves a specific function using its id or label.")
@simple_lookup_key(entity_name=EntityNameEnum.FUNCTION)
@no_type_check
def get(
    id: str | None = None,
    label: str | None = None,
    fields: Annotated[
        str,
        typer.Option(help=FIELDS_FUNCTION_HELP_TEXT),
    ] = DefaultInstanceFieldEnum.get_default_fields(),
    format: OutputFormatFieldsEnum = settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
):
    function_key = get_instance_key(id=id, label=label)

    handlers.retrieve_function(
        function_key=function_key,
        fields=fields,
        format=format,
    )


@app.command(short_help="Lists all available functions.")
@add_pagination_options()
@add_sort_by_option()
@add_filter_option()
@no_type_check
def list(
    fields: Annotated[
        str,
        typer.Option(help=FIELDS_FUNCTION_HELP_TEXT),
    ] = DefaultInstanceFieldEnum.get_default_fields(),
    filter: str | None = None,
    sort_by: str | None = None,
    page_size: int | None = None,
    page: int | None = None,
    format: OutputFormatFieldsEnum = settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
):
    handlers.list_functions(
        fields=fields,
        filter=filter,
        sort_by=sort_by,
        page_size=page_size,
        page=page,
        format=format,
    )


@app.command(short_help="Adds a new function.")
def add(
    name: Annotated[
        str, typer.Argument(help="The name of the function.", show_default=False)
    ],
    label: Annotated[str, typer.Option(help="The label for the function.")] = "",
    runtime: Annotated[
        FunctionRuntimeLayerTypeEnum,
        typer.Option(
            help="The runtime for the function.",
        ),
    ] = FunctionRuntimeLayerTypeEnum.NODEJS_20_LITE,
    raw: Annotated[
        bool,
        typer.Option(help="Flag to determine if the output should be in raw format."),
    ] = False,
    token: Annotated[
        str, typer.Option(help="Optional authentication token to invoke the function.")
    ] = "",
    methods: Annotated[
        str,
        typer.Option(help="The HTTP methods the function will respond to."),
    ] = FunctionMethodEnum.get_default_method(),
    cors: Annotated[
        bool,
        typer.Option(
            help="Flag to enable Cross-Origin Resource Sharing (CORS) for the function.",
        ),
    ] = False,
    cron: Annotated[
        str,
        typer.Option(
            help="Cron expression to schedule the function for periodic execution.",
            hidden=True,
        ),
    ] = settings.FUNCTIONS.DEFAULT_CRON,
    environment: Annotated[
        str,
        typer.Option(help="environment in JSON format.", callback=is_valid_json_string),
    ] = "[]",
):
    handlers.add_function(
        label=label,
        name=name,
        triggers={
            "httpMethods": FunctionMethodEnum.parse_methods_to_enum_list(methods),
            "httpHasCors": cors,
            "schedulerCron": cron,
        },
        serverless={
            "runtime": runtime,
            "isRawFunction": raw,
            "authToken": token or None,
        },
        environment=environment,
    )


@app.command(short_help="Update a function.")
@simple_lookup_key(entity_name=EntityNameEnum.FUNCTION)
def update(
    id: str | None = None,
    label: str | None = None,
    new_label: Annotated[str, typer.Option(help="The label for the device.")] = "",
    new_name: Annotated[str, typer.Option(help="The name of the device.")] = "",
    runtime: Annotated[
        FunctionRuntimeLayerTypeEnum,
        typer.Option(
            help="The runtime for the function.",
        ),
    ] = FunctionRuntimeLayerTypeEnum.NODEJS_20_LITE,
    raw: Annotated[
        bool,
        typer.Option(help="Flag to determine if the output should be in raw format."),
    ] = False,
    token: Annotated[
        str, typer.Option(help="Optional authentication token to invoke the function.")
    ] = "",
    methods: Annotated[
        str,
        typer.Option(help="The HTTP methods the function will respond to."),
    ] = FunctionMethodEnum.get_default_method(),
    cors: Annotated[
        bool,
        typer.Option(
            help="Flag to enable Cross-Origin Resource Sharing (CORS) for the function.",
        ),
    ] = False,
    cron: Annotated[
        str,
        typer.Option(
            help="Cron expression to schedule the function for periodic execution.",
            hidden=True,
        ),
    ] = settings.FUNCTIONS.DEFAULT_CRON,
    environment: Annotated[
        str,
        typer.Option(help="environment in JSON format.", callback=is_valid_json_string),
    ] = "[]",
):
    function_key = get_instance_key(id=id, label=label)

    handlers.update_function(
        function_key=function_key,
        label=new_label,
        name=new_name,
        triggers={
            "httpMethods": FunctionMethodEnum.parse_methods_to_enum_list(methods),
            "httpHasCors": cors,
            "schedulerCron": cron,
        },
        serverless={
            "runtime": runtime,
            "isRawFunction": raw,
            "authToken": token or None,
        },
        environment=environment,
    )
