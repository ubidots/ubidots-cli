from typing import Annotated
from typing import no_type_check

import typer

from cli.apps import executor
from cli.apps.enums import MenuAlignmentEnum
from cli.apps.enums import MenuModeEnum
from cli.commons.decorators import add_filter_option
from cli.commons.decorators import add_pagination_options
from cli.commons.decorators import add_sort_by_option
from cli.commons.decorators import simple_lookup_key
from cli.commons.enums import DefaultInstanceFieldEnum
from cli.commons.enums import EntityNameEnum
from cli.commons.enums import OutputFormatFieldsEnum
from cli.commons.utils import get_instance_key
from cli.config.helpers import get_configuration
from cli.settings import settings

APP_HELP_TEXT = (
    "Tool for managing Ubidots Apps. "
    "Use `ubidots apps list` to discover existing apps and "
    "`ubidots apps menu schema` to print the DTD describing the expected XML structure."
)

MENU_HELP_TEXT = (
    "Manage the sidebar menu XML for an Ubidots App. "
    "Use `ubidots apps menu schema` to see the expected XML grammar."
)

FIELDS_APP_HELP_TEXT = (
    "Comma-separated fields to process * e.g. field1,field2,field3. "
    "* Available fields: (id, label, name, style, customDomain)."
)

app = typer.Typer(help=APP_HELP_TEXT)
menu_app = typer.Typer(help=MENU_HELP_TEXT)


@app.command(name="list", short_help="Lists all available apps.")
@add_pagination_options()
@add_sort_by_option()
@add_filter_option()
@no_type_check
def list_apps(
    fields: Annotated[
        str,
        typer.Option(help=FIELDS_APP_HELP_TEXT),
    ] = DefaultInstanceFieldEnum.get_default_fields(),
    filter: str | None = None,
    sort_by: str | None = None,
    page_size: int | None = None,
    page: int | None = None,
    profile: Annotated[
        str,
        typer.Option(
            help="Name of the profile to use for remote server communication."
        ),
    ] = "",
    format: OutputFormatFieldsEnum = settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
):
    active_config = get_configuration(profile=profile)
    executor.list_apps_cmd(
        active_config=active_config,
        fields=fields,
        filter=filter,
        sort_by=sort_by,
        page_size=page_size,
        page=page,
        format=format,
    )


@menu_app.command(name="get", short_help="Reads the sidebar menu XML for an app.")
@simple_lookup_key(entity_name=EntityNameEnum.APP)
@no_type_check
def menu_get(
    id: str | None = None,
    label: str | None = None,
    profile: Annotated[
        str,
        typer.Option(
            help="Name of the profile to use for remote server communication."
        ),
    ] = "",
    format: OutputFormatFieldsEnum = settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
    output: Annotated[
        str,
        typer.Option(
            "--output",
            "-o",
            help="Optional file path to write the full menu payload (JSON).",
        ),
    ] = "",
):
    app_key = get_instance_key(id=id, label=label)
    active_config = get_configuration(profile=profile)
    executor.get_menu_cmd(
        active_config=active_config,
        app_key=app_key,
        format=format,
        output=output,
    )


@menu_app.command(
    name="set",
    short_help="Updates the sidebar menu XML for an app (V2 DTD validated).",
)
@simple_lookup_key(entity_name=EntityNameEnum.APP)
@no_type_check
def menu_set(
    id: str | None = None,
    label: str | None = None,
    file: Annotated[
        str,
        typer.Option(
            "--file",
            "-f",
            help="Path to a V2 menu XML file. Use '-' to read from stdin.",
        ),
    ] = "",
    alignment: MenuAlignmentEnum = MenuAlignmentEnum.LEFT,
    mode: MenuModeEnum = MenuModeEnum.CUSTOM,
    profile: Annotated[
        str,
        typer.Option(
            help="Name of the profile to use for remote server communication."
        ),
    ] = "",
):
    if not file:
        error_message = "Provide --file <path> (or '-' for stdin)."
        raise typer.BadParameter(error_message)

    app_key = get_instance_key(id=id, label=label)
    active_config = get_configuration(profile=profile)
    executor.set_menu_cmd(
        active_config=active_config,
        app_key=app_key,
        file=file,
        alignment=alignment,
        mode=mode,
    )


@menu_app.command(
    name="reset",
    short_help="Resets the sidebar menu to the platform default (DELETE).",
)
@simple_lookup_key(entity_name=EntityNameEnum.APP)
@no_type_check
def menu_reset(
    id: str | None = None,
    label: str | None = None,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Confirm reset without prompt."),
    ] = False,
    profile: Annotated[
        str,
        typer.Option(
            help="Name of the profile to use for remote server communication."
        ),
    ] = "",
):
    app_key = get_instance_key(id=id, label=label)
    active_config = get_configuration(profile=profile)
    executor.reset_menu_cmd(
        active_config=active_config,
        app_key=app_key,
        yes=yes,
    )


@menu_app.command(
    name="default",
    short_help="Prints the bundled default menu template (offline, no auth).",
)
@no_type_check
def menu_default(
    format: OutputFormatFieldsEnum = settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
):
    executor.default_menu_cmd(format=format)


@menu_app.command(
    name="schema",
    short_help="Prints the bundled V2 DTD describing the menu XML grammar.",
)
def menu_schema():
    executor.print_schema_cmd()


app.add_typer(menu_app, name="menu")
