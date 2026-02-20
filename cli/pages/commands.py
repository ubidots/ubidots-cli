"""Commands for the pages module."""

import typer
from typing_extensions import Annotated

from cli.commons.decorators import add_verbose_option
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


# ============================================================================
# DEV COMMANDS (Local Development)
# ============================================================================


@dev_app.command(name="add", help=DEV_ADD_COMMAND_HELP_TEXT)
@add_verbose_option()
def dev_add(
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
    """Create a new local page or pull from remote.

    If --remote-id is provided, pulls the page from cloud instead of creating locally.
    This functionality will be implemented when cloud page support is added.
    """
    if remote_id:
        # Future: executor.pull_page(remote_id, verbose, profile)
        typer.echo(
            "Remote page pulling not implemented yet. This feature is reserved for "
            "future cloud integration."
        )
        typer.echo(f"Attempted to pull page with ID: {remote_id}")
        return
    else:
        executor.create_page(
            name=name,
            verbose=verbose,
            profile=profile,
            type=type,
        )


@dev_app.command(name="init", hidden=True, help="Deprecated: Use 'dev add' instead.")
@add_verbose_option()
def dev_init(
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
    """Deprecated: Use 'dev add' instead. Kept for backward compatibility."""
    dev_add(
        name=name,
        remote_id=remote_id,
        profile=profile,
        type=type,
        verbose=verbose,
    )


@dev_app.command(help=START_COMMAND_HELP_TEXT)
@add_verbose_option()
def start(
    verbose: bool = False,
):
    executor.start_page(
        verbose=verbose,
    )


@dev_app.command(help=STOP_COMMAND_HELP_TEXT)
@add_verbose_option()
def stop(
    verbose: bool = False,
):
    executor.stop_page(
        verbose=verbose,
    )


@dev_app.command(help=RESTART_COMMAND_HELP_TEXT)
@add_verbose_option()
def restart(
    verbose: bool = False,
):
    executor.restart_page(
        verbose=verbose,
    )


@dev_app.command(help=STATUS_COMMAND_HELP_TEXT)
@add_verbose_option()
def status(
    verbose: bool = False,
):
    executor.status_page(
        verbose=verbose,
    )


@dev_app.command(help=LIST_COMMAND_HELP_TEXT)
@add_verbose_option()
def list(
    verbose: bool = False,
):
    executor.list_pages(
        verbose=verbose,
    )


# Register the dev subcommand
app.add_typer(dev_app, name="dev")
