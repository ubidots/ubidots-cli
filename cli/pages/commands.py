"""Commands for the pages module."""

import typer
from typing_extensions import Annotated

from cli.commons.decorators import add_verbose_option
from cli.pages import executor
from cli.pages.models import PageTypeEnum
from cli.settings import settings

app = typer.Typer(help="Tool for managing and developing Ubidots Pages.")

INIT_COMMAND_HELP_TEXT = (
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


@app.command(help=INIT_COMMAND_HELP_TEXT)
@add_verbose_option()
def init(
    name: Annotated[
        str,
        typer.Option(help="The name for the page."),
    ] = settings.PAGES.DEFAULT_PAGE_NAME,
    remote_id: Annotated[
        str,
        typer.Option(
            "--remote-id",
            help="The remote page ID.",
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
        print("Not implemented yet")
        return 0
    else:
        executor.create_page(
            name=name,
            verbose=verbose,
            profile=profile,
            type=type,
        )


@app.command(help=START_COMMAND_HELP_TEXT)
@add_verbose_option()
def start(
    verbose: bool = False,
):
    executor.start_page(
        verbose=verbose,
    )


@app.command(help=STOP_COMMAND_HELP_TEXT)
@add_verbose_option()
def stop(
    verbose: bool = False,
):
    executor.stop_page(
        verbose=verbose,
    )


@app.command(help=RESTART_COMMAND_HELP_TEXT)
@add_verbose_option()
def restart(
    verbose: bool = False,
):
    executor.restart_page(
        verbose=verbose,
    )


@app.command(help=STATUS_COMMAND_HELP_TEXT)
@add_verbose_option()
def status(
    verbose: bool = False,
):
    executor.status_page(
        verbose=verbose,
    )


@app.command(help=LIST_COMMAND_HELP_TEXT)
@add_verbose_option()
def list(
    verbose: bool = False,
):
    executor.list_pages(
        verbose=verbose,
    )
