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
)

STATUS_COMMAND_HELP_TEXT = (
    "Show the status of the local development server for the Ubidots page. "
)

LIST_COMMAND_HELP_TEXT = "List all pages and their status. "

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
    remote_id: Annotated[
        str,
        typer.Option(
            "--remote-id",
            help="Optional: remote page ID to pull from cloud.",
        ),
    ] = "",
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
        ),
    ] = PageTypeEnum.DASHBOARD,
    verbose: bool = False,
):
    if remote_id:
        # Future: executor.pull_page(remote_id, verbose, profile)
        typer.echo(
            "Remote page pulling not implemented yet. This feature is reserved for "
            "future cloud integration."
        )
        typer.echo(f"Attempted to pull page with ID: {remote_id}")
        return
    executor.create_page(
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
    remote_id: Annotated[
        str,
        typer.Option(
            "--remote-id",
            help="Optional: remote page ID to pull from cloud.",
        ),
    ] = "",
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
        ),
    ] = PageTypeEnum.DASHBOARD,
    verbose: bool = False,
):
    create_page(
        name=name,
        remote_id=remote_id,
        profile=profile,
        type=type,
        verbose=verbose,
    )


@dev_app.command(name="start", help=START_COMMAND_HELP_TEXT)
@add_verbose_option()
def start_page(
    verbose: bool = False,
):
    executor.start_page(
        verbose=verbose,
    )


@dev_app.command(name="stop", help=STOP_COMMAND_HELP_TEXT)
@add_verbose_option()
def stop_page(
    verbose: bool = False,
):
    executor.stop_page(
        verbose=verbose,
    )


@dev_app.command(name="restart", help=RESTART_COMMAND_HELP_TEXT)
@add_verbose_option()
def restart_page(
    verbose: bool = False,
):
    executor.restart_page(
        verbose=verbose,
    )


@dev_app.command(name="status", help=STATUS_COMMAND_HELP_TEXT)
@add_verbose_option()
def status_page(
    verbose: bool = False,
):
    executor.status_page(
        verbose=verbose,
    )


@dev_app.command(name="list", help=LIST_COMMAND_HELP_TEXT)
@add_verbose_option()
def list_pages(
    verbose: bool = False,
):
    executor.list_pages(
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
    executor.list_pages_cloud(
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
    executor.get_page(
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
    executor.add_page_cloud(
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
    executor.delete_page_cloud(
        page_key=page_key,
        profile=profile,
        confirm=confirm,
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
    executor.push_page(
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
    executor.pull_page_cloud(
        remote_id=remote_id,
        profile=profile,
        verbose=verbose,
        confirm=confirm,
    )


app.add_typer(dev_app, name="dev")
