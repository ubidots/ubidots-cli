from typing import Annotated
from typing import no_type_check

import typer

from cli.commons.decorators import add_pagination_options
from cli.commons.decorators import add_sort_by_option
from cli.commons.enums import DefaultInstanceFieldEnum
from cli.commons.enums import OutputFormatFieldsEnum
from cli.config.helpers import get_configuration
from cli.global_properties import handlers
from cli.global_properties.enums import PropertyFormatEnum
from cli.global_properties.helpers import build_add_payload
from cli.global_properties.helpers import build_update_payload
from cli.settings import settings

FIELDS_HELP_TEXT = (
    "Comma-separated fields to process * e.g. field1,field2,field3. "
    "* Available fields: (id, label, name, format, value, isSecret, scope, "
    "description, createdAt, updatedAt, url). "
    "Note: 'value' is masked with asterisks when 'isSecret' is true."
)

app = typer.Typer(
    help=(
        "Manage account-level Global Properties (reusable secrets/config). "
        "Supports CRUD by id or label."
    )
)


@app.command(name="list", short_help="Lists all Global Properties for the account.")
@add_pagination_options()
@add_sort_by_option()
@no_type_check
def list_properties(
    fields: Annotated[
        str,
        typer.Option(help=FIELDS_HELP_TEXT),
    ] = DefaultInstanceFieldEnum.get_default_fields(),
    search: Annotated[
        str | None,
        typer.Option(help="Substring search across label/name/description."),
    ] = None,
    created_after: Annotated[
        str | None,
        typer.Option(
            "--created-after",
            help="ISO 8601 timestamp (e.g. 2026-01-01T00:00:00Z); filters by createdAt >=.",
        ),
    ] = None,
    updated_after: Annotated[
        str | None,
        typer.Option(
            "--updated-after",
            help="ISO 8601 timestamp; filters by updatedAt >=.",
        ),
    ] = None,
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
    handlers.list_properties(
        active_config=active_config,
        fields=fields,
        search=search,
        sort_by=sort_by,
        page_size=page_size,
        page=page,
        created_after=created_after,
        updated_after=updated_after,
        output_format=format,
    )


@app.command(name="get", short_help="Retrieve a Global Property by id or label.")
@no_type_check
def get_property(
    key: Annotated[
        str,
        typer.Argument(
            help="Property id or label.",
            show_default=False,
        ),
    ],
    fields: Annotated[
        str,
        typer.Option(help=FIELDS_HELP_TEXT),
    ] = DefaultInstanceFieldEnum.get_default_fields(),
    profile: Annotated[
        str,
        typer.Option(
            help="Name of the profile to use for remote server communication."
        ),
    ] = "",
    format: OutputFormatFieldsEnum = settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
):
    active_config = get_configuration(profile=profile)
    handlers.retrieve_property(
        active_config=active_config,
        property_key=key,
        fields=fields,
        output_format=format,
    )


@app.command(name="add", short_help="Create a new Global Property.")
@no_type_check
def add_property(
    label: Annotated[
        str,
        typer.Option(
            "--label", help="Unique label for the property.", show_default=False
        ),
    ],
    value: Annotated[
        str,
        typer.Option(
            "--value", help="The value (typed via --format).", show_default=False
        ),
    ],
    format: Annotated[
        PropertyFormatEnum,
        typer.Option(
            "--format", help="Type of the value: string, int, float, bool, json."
        ),
    ] = PropertyFormatEnum.STRING,
    name: Annotated[
        str,
        typer.Option("--name", help="Human-friendly name. Defaults to the label."),
    ] = "",
    description: Annotated[
        str,
        typer.Option("--description", help="Optional description."),
    ] = "",
    scope: Annotated[
        str,
        typer.Option(
            "--scope",
            help="Comma-separated scope tags (e.g. 'functions,pages'). Empty = all.",
        ),
    ] = "",
    secret: Annotated[
        bool,
        typer.Option(
            "--secret",
            help="Mark the property as secret (value will be masked on read).",
        ),
    ] = False,
    profile: Annotated[
        str,
        typer.Option(
            help="Name of the profile to use for remote server communication."
        ),
    ] = "",
):
    active_config = get_configuration(profile=profile)
    payload = build_add_payload(
        label=label,
        value_format=format,
        value=value,
        name=name,
        description=description,
        scope=scope,
        is_secret=secret,
    )
    handlers.add_property(active_config=active_config, payload=payload)


@app.command(name="update", short_help="Update fields of an existing Global Property.")
@no_type_check
def update_property(
    key: Annotated[
        str,
        typer.Argument(help="Property id or label.", show_default=False),
    ],
    value: Annotated[
        str | None,
        typer.Option(
            "--value",
            help=(
                "New value. If omitted, the value is NOT touched (avoids "
                "overwriting a secret with its masked representation)."
            ),
        ),
    ] = None,
    format: Annotated[
        PropertyFormatEnum | None,
        typer.Option(
            "--format",
            help="Required when --value is passed. Type to coerce the value into.",
        ),
    ] = None,
    name: Annotated[
        str,
        typer.Option("--name", help="New name."),
    ] = "",
    description: Annotated[
        str,
        typer.Option("--description", help="New description."),
    ] = "",
    scope: Annotated[
        str | None,
        typer.Option(
            "--scope",
            help="Comma-separated scope tags. Pass empty string to clear (`--scope ''`).",
        ),
    ] = None,
    secret: Annotated[
        bool | None,
        typer.Option(
            "--secret/--no-secret",
            help="Mark/unmark the property as secret.",
        ),
    ] = None,
    profile: Annotated[
        str,
        typer.Option(
            help="Name of the profile to use for remote server communication."
        ),
    ] = "",
):
    active_config = get_configuration(profile=profile)
    payload = build_update_payload(
        value=value,
        value_format=format,
        name=name,
        description=description,
        scope=scope,
        is_secret=secret,
    )
    handlers.update_property(
        active_config=active_config, property_key=key, payload=payload
    )


@app.command(name="delete", short_help="Delete a Global Property by id or label.")
def delete_property(
    key: Annotated[
        str,
        typer.Argument(help="Property id or label.", show_default=False),
    ],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip the confirmation prompt."),
    ] = False,
    profile: Annotated[
        str,
        typer.Option(
            help="Name of the profile to use for remote server communication."
        ),
    ] = "",
):
    active_config = get_configuration(profile=profile)
    if not yes:
        typer.confirm(
            f"Delete Global Property '{key}'? This cannot be undone.",
            abort=True,
        )
    handlers.delete_property(active_config=active_config, property_key=key)
