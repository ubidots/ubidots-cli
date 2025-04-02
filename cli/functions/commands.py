from builtins import list as BuiltinList
from datetime import datetime
from typing import Annotated
from typing import Union
from typing import no_type_check

import typer

from cli.commons.decorators import add_filter_option
from cli.commons.decorators import add_pagination_options
from cli.commons.decorators import add_sort_by_option
from cli.commons.decorators import add_verbose_option
from cli.commons.decorators import simple_lookup_key
from cli.commons.enums import DefaultInstanceFieldEnum
from cli.commons.enums import EntityNameEnum
from cli.commons.enums import OutputFormatFieldsEnum
from cli.commons.utils import get_instance_key
from cli.commons.utils import sanitize_function_name
from cli.commons.validators import is_valid_json_string
from cli.functions import executor
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.enums import FunctionMethodEnum
from cli.functions.enums import FunctionRuntimeLayerTypeEnum
from cli.settings import settings

DEFAULT_METHODS = FunctionMethodEnum.get_default_method()
FIELDS_FUNCTION_HELP_TEXT = (
    "Comma-separated fields to process * e.g. field1,field2,field3. "
    "* Available fields: (url, id, label, name, isActive, createdAt, serverless, "
    "triggers, environment, zipFileProperties)."
)
INIT_COMMAND_HELP_TEXT = (
    "Create a new local function. If the `--remote-id` option is used, "
    "the corresponding function will be pulled from the remote server instead."
)


app = typer.Typer(help="Tool for managing and deploying functions.")


@app.command(help=INIT_COMMAND_HELP_TEXT, hidden=False)
@add_verbose_option()
def init(
    name: Annotated[
        str,
        typer.Option(help="The name for the function."),
    ] = settings.FUNCTIONS.DEFAULT_PROJECT_NAME,
    language: Annotated[
        FunctionLanguageEnum,
        typer.Option(
            help="The programming language for the function.",
        ),
    ] = settings.FUNCTIONS.DEFAULT_LANGUAGE,
    remote_id: Annotated[
        str,
        typer.Option(
            "--remote-id",
            help="The remote function ID.",
        ),
    ] = "",
    runtime: Annotated[
        FunctionRuntimeLayerTypeEnum,
        typer.Option(
            help="The runtime for the function.",
        ),
    ] = settings.FUNCTIONS.DEFAULT_RUNTIME,
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
    timeout: Annotated[
        int,
        typer.Option(
            help="Timeout for the function in seconds.",
            hidden=True,
        ),
    ] = settings.FUNCTIONS.DEFAULT_TIMEOUT_SECONDS,
    methods: Annotated[
        BuiltinList[FunctionMethodEnum],
        typer.Option(
            help="The HTTP methods the function will respond to.",
        ),
    ] = settings.FUNCTIONS.DEFAULT_METHODS,
    raw: Annotated[
        bool,
        typer.Option(
            help="Flag to determine if the output should be in raw format.",
        ),
    ] = settings.FUNCTIONS.DEFAULT_IS_RAW,
    token: Annotated[
        str,
        typer.Option(
            help="Token used to invoke the function.",
        ),
    ] = "",
    profile: Annotated[
        str,
        typer.Option(
            help="Profile to use.",
        ),
    ] = "",
    verbose: bool = False,
):
    if remote_id:
        executor.pull_function(
            remote_id=remote_id,
            verbose=verbose,
            profile=profile,
        )
    else:
        executor.create_function(
            name=name,
            language=language,
            runtime=runtime,
            methods=methods,
            is_raw=raw,
            cron=cron,
            cors=cors,
            verbose=verbose,
            timeout=timeout,
            created_at=datetime.now().isoformat(),
            engine=settings.CONFIG.DEFAULT_CONTAINER_ENGINE,
            token=token,
            profile=profile,
        )


@app.command(help="Start Function.", hidden=True)
@add_verbose_option()
def start(
    verbose: bool = False,
):
    executor.start_function(
        verbose=verbose,
    )


@app.command(help="Stop the function.")
@add_verbose_option()
def stop(
    verbose: bool = False,
):
    executor.stop_function(
        verbose=verbose,
    )


@app.command(help="Restart the function.")
@add_verbose_option()
def restart(
    verbose: bool = False,
):
    executor.restart_function(
        verbose=verbose,
    )


@app.command(help="Check the status of the functions.")
@add_verbose_option()
def status(
    verbose: bool = False,
):
    executor.status_function(
        verbose=verbose,
    )


@app.command(help="Get logs from the function.", hidden=True)
@add_verbose_option()
def logs(
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
    profile: Annotated[
        str,
        typer.Option(
            "--profile/",
            "-p/",
            help="Profile to use.",
        ),
    ] = "",
    remote: Annotated[
        bool,
        typer.Option("--remote/", "-r/", help="Fetch logs from the remote server."),
    ] = False,
    verbose: bool = False,
):
    executor.logs_function(
        tail=tail,
        follow=follow,
        remote=remote,
        profile=profile,
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
    profile: Annotated[
        str,
        typer.Option("--profile", "-p", help="Profile to use."),
    ] = "",
    verbose: bool = False,
):
    executor.push_function(
        confirm=confirm,
        profile=profile,
        verbose=verbose,
    )


@app.command(
    help="Retrieve and update your local function code with the latest changes from the remote server.",
)
@add_verbose_option()
def pull(
    remote_id: Annotated[
        str,
        typer.Option("--remote-id", "-i", help="The remote function ID."),
    ] = "",
    profile: Annotated[
        str,
        typer.Option("--profile", "-p", help="Profile to use."),
    ] = "",
    confirm: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Confirm file overwrite without prompt."),
    ] = False,
    verbose: bool = False,
):
    executor.pull_function(
        remote_id=remote_id,
        profile=profile,
        verbose=verbose,
        confirm=confirm,
    )


@app.command(
    help="Clean up functions environment to ensure a fresh start.", hidden=True
)
@add_verbose_option()
def clean(
    confirm: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Confirm file overwrite without prompt."),
    ] = False,
    verbose: bool = False,
):
    executor.clean_functions(
        confirm=confirm,
        verbose=verbose,
    )


@app.command(short_help="Lists all available functions.")
@add_pagination_options()
@add_sort_by_option()
@add_filter_option()
@no_type_check
def list(
    profile: Annotated[
        str,
        typer.Option(
            help="Name of the profile to use for remote server communication."
        ),
    ] = "",
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
    executor.list_functions(
        profile=profile,
        fields=fields,
        filter=filter,
        sort_by=sort_by,
        page_size=page_size,
        page=page,
        format=format,
    )


# CRUD: Create
@app.command(short_help="Adds a new function in the remote server.")
def add(
    name: Annotated[
        str, typer.Argument(help="The name of the function.", show_default=False)
    ],
    profile: Annotated[
        str,
        typer.Option(
            help="Name of the profile to use for remote server communication."
        ),
    ] = "",
    label: Annotated[str, typer.Option(help="The label for the function.")] = "",
    timeout: Annotated[
        int,
        typer.Option(
            help="Timeout for the function in seconds.",
        ),
    ] = settings.FUNCTIONS.DEFAULT_TIMEOUT_SECONDS,
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
    methods: Annotated[
        BuiltinList[FunctionMethodEnum],
        typer.Option(
            help="The HTTP methods the function will respond to.",
        ),
    ] = settings.FUNCTIONS.DEFAULT_METHODS,
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
    label = label or sanitize_function_name(name)
    executor.add_function(
        profile=profile,
        name=name,
        label=label,
        runtime=runtime,
        is_raw=raw,
        http_methods=[method.value for method in methods],
        http_has_cors=cors,
        scheduler_cron=cron,
        timeout=timeout,
        environment=environment,
    )


# CRUD: Read
@app.command(short_help="Retrieves a specific function using its id or label.")
@simple_lookup_key(entity_name=EntityNameEnum.FUNCTION)
@no_type_check
def get(
    profile: Annotated[
        str,
        typer.Option(
            help="Name of the profile to use for remote server communication."
        ),
    ] = "",
    id: str | None = None,
    label: str | None = None,
    fields: Annotated[
        str,
        typer.Option(help=FIELDS_FUNCTION_HELP_TEXT),
    ] = DefaultInstanceFieldEnum.get_default_fields(),
    format: OutputFormatFieldsEnum = settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
    verbose: bool = False,
):
    function_key = get_instance_key(id=id, label=label)

    executor.get_function(
        function_key=function_key,
        fields=fields,
        format=format,
        profile=profile,
        verbose=verbose,
    )


# CRUD: Update
@app.command(short_help="Update a function.")
@simple_lookup_key(entity_name=EntityNameEnum.FUNCTION)
def update(
    id: str | None = None,
    label: str | None = None,
    new_label: Annotated[str, typer.Option(help="The label for the device.")] = "",
    new_name: Annotated[str, typer.Option(help="The name of the device.")] = "",
    runtime: Annotated[
        Union[FunctionRuntimeLayerTypeEnum, None],
        typer.Option(
            help="The runtime for the function.",
        ),
    ] = None,
    raw: Annotated[
        Union[bool, None],
        typer.Option(help="Flag to determine if the output should be in raw format."),
    ] = None,
    cors: Annotated[
        Union[bool, None],
        typer.Option(
            help="Flag to enable Cross-Origin Resource Sharing (CORS) for the function.",
        ),
    ] = None,
    cron: Annotated[
        Union[str, None],
        typer.Option(
            help="Cron expression to schedule the function for periodic execution.",
        ),
    ] = None,
    timeout: Annotated[
        Union[int, None],
        typer.Option(
            help="Timeout for the function in seconds.",
        ),
    ] = None,
    environment: Annotated[
        str,
        typer.Option(help="environment in JSON format.", callback=is_valid_json_string),
    ] = "[]",
    profile: Annotated[
        str,
        typer.Option(
            help="Name of the profile to use for remote server communication."
        ),
    ] = "",
    methods: Annotated[
        Union[BuiltinList[FunctionMethodEnum], None],
        typer.Option(
            help="The HTTP methods the function will respond to.",
        ),
    ] = None,
):
    function_key = get_instance_key(id=id, label=label)

    executor.update_function(
        function_key=function_key,
        profile=profile,
        name=new_name,
        label=new_label,
        http_methods=[method.value for method in methods] if methods else None,
        http_has_cors=cors,
        scheduler_cron=cron,
        runtime=runtime,
        is_raw=raw,
        timeout=timeout,
        environment=environment,
    )


# CRUD: Delete.
@app.command(short_help="Deletes a specific function using its id or label.")
@simple_lookup_key(entity_name=EntityNameEnum.FUNCTION)
def delete(
    profile: Annotated[
        str,
        typer.Option(
            help="Name of the profile to use for remote server communication."
        ),
    ] = "",
    id: str | None = None,
    label: str | None = None,
    confirm: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Confirm file overwrite without prompt."),
    ] = False,
    verbose: bool = False,
):
    function_key = get_instance_key(id=id, label=label)

    executor.delete_function(
        function_key=function_key,
        profile=profile,
        confirm=confirm,
        verbose=verbose,
    )
