from builtins import list as BuiltinList
from datetime import datetime
from typing import Annotated
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
from cli.settings import settings

DEFAULT_METHODS = FunctionMethodEnum.get_default_method()
FIELDS_FUNCTION_HELP_TEXT = (
    "Comma-separated fields to process * e.g. field1,field2,field3. "
    "* Available fields: (url, id, label, name, isActive, createdAt, serverless, "
    "triggers, environment, zipFileProperties)."
)
DEV_ADD_COMMAND_HELP_TEXT = (
    "Create a new local function project with starter code and configuration."
)


app = typer.Typer(help="Tool for managing and deploying functions.")
dev_app = typer.Typer(help="Local development commands for functions.")


@dev_app.command(name="add", help=DEV_ADD_COMMAND_HELP_TEXT)
@add_verbose_option()
def create_function(
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
    runtime: Annotated[
        str,
        typer.Option(
            help=(
                "Runtime for the function (e.g. 'python3.11:lite', 'nodejs20.x:lite'). "
                "Allowed values depend on your account — if the runtime is rejected, "
                "check your available runtimes in the Ubidots platform."
            ),
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


@dev_app.command(name="init", hidden=True, help="Deprecated: Use 'dev add' instead.")
@add_verbose_option()
def create_function_deprecated(
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
    runtime: Annotated[
        str,
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


@dev_app.command(name="start", help="Start the local functions development server.")
@add_verbose_option()
def start_function(
    verbose: bool = False,
):
    executor.start_function(
        verbose=verbose,
    )


@dev_app.command(name="stop", help="Stop the local functions development server.")
@add_verbose_option()
def stop_function(
    verbose: bool = False,
):
    executor.stop_function(
        verbose=verbose,
    )


@dev_app.command(name="restart", help="Restart the local functions development server.")
@add_verbose_option()
def restart_function(
    verbose: bool = False,
):
    executor.restart_function(
        verbose=verbose,
    )


@dev_app.command(
    name="status", help="Check the status of the local functions development server."
)
@add_verbose_option()
def status_function(
    verbose: bool = False,
):
    executor.status_function(
        verbose=verbose,
    )


@dev_app.command(
    name="logs", help="Display logs from the local functions development server."
)
@add_verbose_option()
def logs_function_local(
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
    verbose: bool = False,
):
    """Display logs from the local function development server.

    This command shows logs from your local Docker/Podman container.
    For cloud function logs, use 'ubidots functions logs <function-id>'.
    """
    executor.logs_function(
        tail=tail,
        follow=follow,
        remote=False,
        profile="",
        verbose=verbose,
    )


@dev_app.command(name="clean", help="Clean up local functions development environment.")
@add_verbose_option()
def clean_functions(
    confirm: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Confirm cleanup without prompt."),
    ] = False,
    verbose: bool = False,
):
    executor.clean_functions(
        confirm=confirm,
        verbose=verbose,
    )


@app.command(
    name="run",
    short_help="Trigger a remote function.",
    rich_help_panel="Cloud Commands",
)
@simple_lookup_key(entity_name=EntityNameEnum.FUNCTION)
@add_verbose_option()
def run_function(
    id: str | None = None,
    label: str | None = None,
    payload: Annotated[
        str,
        typer.Option(
            help="JSON payload to send to the function.",
            callback=is_valid_json_string,
        ),
    ] = "{}",
    profile: Annotated[
        str,
        typer.Option(
            help="Name of the profile to use for remote server communication."
        ),
    ] = "",
    verbose: bool = False,
):
    function_key = get_instance_key(id=id, label=label)

    executor.run_function(
        function_key=function_key,
        # `is_valid_json_string` callback above transforms str → dict at parse time;
        # mypy still sees the Annotated type (str) so we suppress here.
        payload=payload,  # type: ignore[arg-type]
        profile=profile,
        verbose=verbose,
    )


@app.command(
    name="logs",
    help="Retrieve and display logs from a remote function.",
    rich_help_panel="Cloud Commands",
)
@simple_lookup_key(entity_name=EntityNameEnum.FUNCTION)
@add_verbose_option()
def logs_function_remote(
    id: str | None = None,
    label: str | None = None,
    tail: Annotated[
        int,
        typer.Option(
            "--tail",
            "-n",
            help="Number of most recent activations to show (detailed). Defaults to 1.",
        ),
    ] = 1,
    profile: Annotated[
        str,
        typer.Option(
            "--profile",
            "-p",
            help="Profile to use for remote server communication.",
        ),
    ] = "",
    verbose: bool = False,
):
    function_key = get_instance_key(id=id, label=label)

    executor.logs_function(
        tail=tail,
        follow=False,
        remote=True,
        function_key=function_key,
        profile=profile,
        verbose=verbose,
    )


@app.command(
    name="list",
    short_help="Lists all available functions.",
    rich_help_panel="Cloud Commands",
)
@add_pagination_options()
@add_sort_by_option()
@add_filter_option()
@no_type_check
def list_functions(
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
@app.command(
    name="add",
    short_help="Adds a new function in the remote server.",
    rich_help_panel="Cloud Commands",
)
def add_function(
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
        str,
        typer.Option(
            help="The runtime for the function.",
        ),
    ] = settings.FUNCTIONS.DEFAULT_RUNTIME,
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
@app.command(
    name="get",
    short_help="Retrieves a specific function using its id or label.",
    rich_help_panel="Cloud Commands",
)
@simple_lookup_key(entity_name=EntityNameEnum.FUNCTION)
@no_type_check
def get_function(
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
@app.command(
    name="update", short_help="Update a function.", rich_help_panel="Cloud Commands"
)
@simple_lookup_key(entity_name=EntityNameEnum.FUNCTION)
def update_function(
    id: str | None = None,
    label: str | None = None,
    new_label: Annotated[str, typer.Option(help="The label for the device.")] = "",
    new_name: Annotated[str, typer.Option(help="The name of the device.")] = "",
    runtime: Annotated[
        str | None,
        typer.Option(
            help="The runtime for the function.",
        ),
    ] = None,
    raw: Annotated[
        bool | None,
        typer.Option(help="Flag to determine if the output should be in raw format."),
    ] = None,
    cors: Annotated[
        bool | None,
        typer.Option(
            help="Flag to enable Cross-Origin Resource Sharing (CORS) for the function.",
        ),
    ] = None,
    cron: Annotated[
        str | None,
        typer.Option(
            help="Cron expression to schedule the function for periodic execution.",
        ),
    ] = None,
    timeout: Annotated[
        int | None,
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
        BuiltinList[FunctionMethodEnum] | None,
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
@app.command(
    name="delete",
    short_help="Deletes a specific function using its id or label.",
    rich_help_panel="Cloud Commands",
)
@simple_lookup_key(entity_name=EntityNameEnum.FUNCTION)
def delete_function(
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


@app.command(
    name="push",
    help="Update and synchronize your local function code with the remote server.",
    rich_help_panel="Sync Commands",
)
@add_verbose_option()
def push_function(
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
    name="pull",
    help="Retrieve and update your local function code with the latest changes from the remote server.",
    rich_help_panel="Sync Commands",
)
@add_verbose_option()
def pull_function(
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


# Register the dev subcommand
app.add_typer(dev_app, name="dev")
