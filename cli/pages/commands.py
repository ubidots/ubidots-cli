from typing import Annotated
from typing import no_type_check

import typer

from cli.commons.decorators import add_pagination_options
from cli.commons.decorators import add_sort_by_option
from cli.commons.decorators import add_verbose_option
from cli.commons.decorators import simple_lookup_key
from cli.commons.enums import DefaultInstanceFieldEnum
from cli.commons.enums import EntityNameEnum
from cli.commons.enums import OutputFormatFieldsEnum
from cli.commons.utils import get_instance_key
from cli.commons.utils import sanitize_function_name
from cli.pages import executor
from cli.pages.models import PageTypeEnum
from cli.settings import settings

app = typer.Typer(help="Tool for managing and developing Ubidots Pages.")
dev_app = typer.Typer(help="Local development commands for Ubidots pages.")

DEV_ADD_COMMAND_HELP_TEXT = (
    "Create a new local Ubidots page with default structure and content. "
    "This command creates a directory with all required files."
)

START_COMMAND_HELP_TEXT = "Start the local development server for the Ubidots page. "

STOP_COMMAND_HELP_TEXT = "Stop the local development server for the Ubidots page. "

RESTART_COMMAND_HELP_TEXT = (
    "Restart the local development server for the Ubidots page. "
    "The page must already be running; use 'dev start' first if it is stopped."
)

STATUS_COMMAND_HELP_TEXT = (
    "Show the status of the local development server for the Ubidots page. "
)

LIST_COMMAND_HELP_TEXT = "List all pages and their status. "

CLEAN_COMMAND_HELP_TEXT = (
    "Remove orphaned pages whose source directory no longer exists. "
    "Deregisters each page from Argo and deletes its workspace directory."
)

LOGS_COMMAND_HELP_TEXT = "Display logs from the local page development server. "

FIELDS_PAGE_HELP_TEXT = (
    "Comma-separated fields to process * e.g. field1,field2,field3. "
    "* Available fields: (id, label, name, url, isActive, createdAt, settings)."
)


@dev_app.command(name="add", help=DEV_ADD_COMMAND_HELP_TEXT)
@add_verbose_option()
def create_page(
    name: Annotated[
        str,
        typer.Option(help="The name for the page."),
    ] = settings.PAGES.DEFAULT_PAGE_NAME,
    profile: Annotated[
        str,
        typer.Option(
            help="Profile to use.",
        ),
    ] = "",
    type: Annotated[
        PageTypeEnum,
        typer.Option(
            help="The type of page to create.",
            hidden=True,
        ),
    ] = PageTypeEnum.DASHBOARD,
    verbose: bool = False,
):
    executor.create_local_page(
        name=name,
        verbose=verbose,
        profile=profile,
        type=type,
    )


@dev_app.command(name="init", hidden=True, help="Deprecated: Use 'dev add' instead.")
@add_verbose_option()
def create_page_deprecated(
    name: Annotated[
        str,
        typer.Option(help="The name for the page."),
    ] = settings.PAGES.DEFAULT_PAGE_NAME,
    profile: Annotated[
        str,
        typer.Option(
            help="Profile to use.",
        ),
    ] = "",
    type: Annotated[
        PageTypeEnum,
        typer.Option(
            help="The type of page to create.",
            hidden=True,
        ),
    ] = PageTypeEnum.DASHBOARD,
    verbose: bool = False,
):
    create_page(
        name=name,
        profile=profile,
        type=type,
        verbose=verbose,
    )


@dev_app.command(name="start", help=START_COMMAND_HELP_TEXT)
@add_verbose_option()
def start_page(
    verbose: bool = False,
):
    executor.start_local_dev_server(
        verbose=verbose,
    )


@dev_app.command(name="stop", help=STOP_COMMAND_HELP_TEXT)
@add_verbose_option()
def stop_page(
    verbose: bool = False,
):
    executor.stop_local_dev_server(
        verbose=verbose,
    )


@dev_app.command(name="restart", help=RESTART_COMMAND_HELP_TEXT)
@add_verbose_option()
def restart_page(
    verbose: bool = False,
):
    executor.restart_local_dev_server(
        verbose=verbose,
    )


@dev_app.command(name="status", help=STATUS_COMMAND_HELP_TEXT)
@add_verbose_option()
def status_page(
    verbose: bool = False,
):
    executor.show_local_dev_server_status(
        verbose=verbose,
    )


@dev_app.command(name="list", help=LIST_COMMAND_HELP_TEXT)
@add_verbose_option()
def list_pages(
    verbose: bool = False,
):
    executor.list_local_pages(
        verbose=verbose,
    )


@dev_app.command(name="clean", help=CLEAN_COMMAND_HELP_TEXT)
@add_verbose_option()
def clean_pages(
    confirm: Annotated[
        bool,
        typer.Option(
            "--yes", "-y", help="Skip confirmation prompt and remove immediately."
        ),
    ] = False,
    verbose: bool = False,
):
    executor.clean_orphaned_pages(confirm=confirm, verbose=verbose)


@dev_app.command(name="logs", help=LOGS_COMMAND_HELP_TEXT)
@add_verbose_option()
def logs_page(
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
    """Shows dev server logs. Not yet implemented for the Argo-based engine."""
    executor.logs_local_dev_server(
        tail=tail,
        follow=follow,
        verbose=verbose,
    )


@app.command(
    name="list",
    short_help="Lists all available pages.",
    rich_help_panel="Cloud Commands",
)
@add_pagination_options()
@add_sort_by_option()
@no_type_check
def list_pages_cloud(
    profile: Annotated[
        str,
        typer.Option(
            help="Name of the profile to use for remote server communication."
        ),
    ] = "",
    fields: Annotated[
        str,
        typer.Option(help=FIELDS_PAGE_HELP_TEXT),
    ] = DefaultInstanceFieldEnum.get_default_fields(),
    sort_by: str | None = None,
    page_size: int | None = None,
    page: int | None = None,
    format: OutputFormatFieldsEnum = settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
):
    executor.list_pages_from_cloud_platform(
        profile=profile,
        fields=fields,
        sort_by=sort_by,
        page_size=page_size,
        page=page,
        format=format,
    )


@app.command(
    name="get",
    short_help="Retrieves a specific page using its id or label.",
    rich_help_panel="Cloud Commands",
)
@simple_lookup_key(entity_name=EntityNameEnum.PAGE)
@no_type_check
def get_page(
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
        typer.Option(help=FIELDS_PAGE_HELP_TEXT),
    ] = DefaultInstanceFieldEnum.get_default_fields(),
    format: OutputFormatFieldsEnum = settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
    verbose: bool = False,
):
    page_key = get_instance_key(id=id, label=label)
    executor.get_page_from_cloud_platform(
        page_key=page_key,
        profile=profile,
        verbose=verbose,
        format=format,
        fields=fields,
    )


@app.command(
    name="add",
    short_help="Adds a new page in the remote server.",
    rich_help_panel="Cloud Commands",
)
def add_page(
    name: Annotated[
        str, typer.Argument(help="The name of the page.", show_default=False)
    ],
    profile: Annotated[
        str,
        typer.Option(
            help="Name of the profile to use for remote server communication."
        ),
    ] = "",
    label: Annotated[str, typer.Option(help="The label for the page.")] = "",
):
    label = label or sanitize_function_name(name)
    executor.add_page_to_cloud_platform(
        profile=profile,
        name=name,
        label=label,
    )


@app.command(
    name="delete",
    short_help="Deletes a specific page using its id or label.",
    rich_help_panel="Cloud Commands",
)
@simple_lookup_key(entity_name=EntityNameEnum.PAGE)
def delete_page(
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
        typer.Option("--yes", "-y", help="Confirm deletion without prompt."),
    ] = False,
    verbose: bool = False,
):
    page_key = get_instance_key(id=id, label=label)
    executor.delete_page_from_cloud_platform(
        page_key=page_key,
        profile=profile,
        confirm=confirm,
        verbose=verbose,
    )


@app.command(
    name="update",
    short_help="Updates a specific page using its id or label.",
    rich_help_panel="Cloud Commands",
)
@simple_lookup_key(entity_name=EntityNameEnum.PAGE)
def update_page(
    profile: Annotated[
        str,
        typer.Option(
            help="Name of the profile to use for remote server communication."
        ),
    ] = "",
    id: str | None = None,
    label: str | None = None,
    new_name: Annotated[
        str,
        typer.Option("--new-name", help="New name for the page."),
    ] = "",
    new_label: Annotated[
        str,
        typer.Option("--new-label", help="New label for the page."),
    ] = "",
    verbose: bool = False,
):
    if not new_name and not new_label:
        typer.echo(
            "Error: at least one of --new-name or --new-label is required.", err=True
        )
        raise typer.Exit(1)
    page_key = get_instance_key(id=id, label=label)
    executor.update_page_from_cloud_platform(
        page_key=page_key,
        new_name=new_name,
        new_label=new_label,
        profile=profile,
        verbose=verbose,
    )


@app.command(
    name="push",
    help="Update and synchronize your local page code with the remote server.",
    rich_help_panel="Sync Commands",
)
@add_verbose_option()
def push_page(
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
    executor.push_page_to_cloud_platform(
        confirm=confirm,
        profile=profile,
        verbose=verbose,
    )


@app.command(
    name="pull",
    help="Retrieve and update your local page code with the latest changes from the remote server.",
    rich_help_panel="Sync Commands",
)
@add_verbose_option()
def pull_page(
    remote_id: Annotated[
        str,
        typer.Option("--remote-id", "-i", help="The remote page ID."),
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
    executor.pull_page_from_cloud_platform(
        remote_id=remote_id,
        profile=profile,
        verbose=verbose,
        confirm=confirm,
    )


app.add_typer(dev_app, name="dev")
