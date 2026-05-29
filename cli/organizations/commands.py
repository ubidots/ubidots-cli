import sys
from typing import Annotated
from typing import no_type_check

import typer

from cli.commons.decorators import add_pagination_options
from cli.commons.enums import OutputFormatFieldsEnum
from cli.commons.formatters import resolve_formatter
from cli.config.helpers import get_configuration
from cli.organizations import handlers
from cli.organizations.constants import FIELDS_ORG_HELP_TEXT
from cli.organizations.constants import FIELDS_ORG_LIST_DEFAULT

app = typer.Typer(help="Organization management and operations.")
users_app = typer.Typer(help="Manage users within an organization.")


def _org_key(org_id: str | None, label: str | None) -> str:
    return org_id if org_id is not None else f"~{label}"


@app.command(name="list", short_help="Lists all available organizations.")
@add_pagination_options()
@no_type_check
def list_organizations(
    profile: Annotated[
        str,
        typer.Option(help="Name of the profile to use for remote server communication."),
    ] = "",
    fields: Annotated[
        str,
        typer.Option(help=FIELDS_ORG_HELP_TEXT),
    ] = FIELDS_ORG_LIST_DEFAULT,
    page_size: int | None = None,
    page: int | None = None,
    output_format: Annotated[
        OutputFormatFieldsEnum | None,
        typer.Option("--format"),
    ] = None,
):
    active_config = get_configuration(profile=profile)
    formatter = resolve_formatter(flag=output_format, active_config=active_config, command="organizations list")
    handlers.list_organizations(
        active_config=active_config,
        fields=fields,
        page_size=page_size,
        page=page,
        formatter=formatter,
    )


@app.command(name="get", short_help="Retrieves a specific organization by id or label.")
@no_type_check
def get_organization(
    org_id: Annotated[
        str | None,
        typer.Option("--id", help="Unique identifier for the organization.", show_default=False),
    ] = None,
    label: Annotated[
        str | None,
        typer.Option(help="Descriptive label identifier for the organization.", show_default=False),
    ] = None,
    profile: Annotated[
        str,
        typer.Option(help="Name of the profile to use for remote server communication."),
    ] = "",
    output_format: Annotated[
        OutputFormatFieldsEnum | None,
        typer.Option("--format"),
    ] = None,
):
    if org_id is not None and label is not None:
        typer.echo("Error: flags --id and --label are mutually exclusive.", err=True)
        raise typer.Exit(1)
    if org_id is None and label is None:
        typer.echo("Error: provide --id or --label.", err=True)
        raise typer.Exit(1)

    org_key = _org_key(org_id, label)
    active_config = get_configuration(profile=profile)
    formatter = resolve_formatter(flag=output_format, active_config=active_config, command="organizations get")
    handlers.get_organization(
        org_id=org_key,
        active_config=active_config,
        formatter=formatter,
    )


@app.command(name="create", short_help="Creates a new organization.")
def create_organization(
    name: Annotated[
        str | None,
        typer.Option(help="Name for the new organization.", show_default=False),
    ] = None,
    profile: Annotated[
        str,
        typer.Option(help="Name of the profile to use for remote server communication."),
    ] = "",
    output_format: Annotated[
        OutputFormatFieldsEnum | None,
        typer.Option("--format"),
    ] = None,
):
    if not name:
        typer.echo("Error: flag --name is required.", err=True)
        raise typer.Exit(1)

    active_config = get_configuration(profile=profile)
    formatter = resolve_formatter(flag=output_format, active_config=active_config, command="organizations create")
    handlers.create_organization(
        name=name,
        active_config=active_config,
        formatter=formatter,
    )


@app.command(name="update", short_help="Updates an existing organization.")
def update_organization(
    org_id: Annotated[
        str,
        typer.Option("--id", help="Unique identifier for the organization.", show_default=False),
    ],
    name: Annotated[
        str | None,
        typer.Option(help="New name for the organization.", show_default=False),
    ] = None,
    profile: Annotated[
        str,
        typer.Option(help="Name of the profile to use for remote server communication."),
    ] = "",
    output_format: Annotated[
        OutputFormatFieldsEnum | None,
        typer.Option("--format"),
    ] = None,
):
    if name is None:
        typer.echo("Error: at least one field to update must be provided.", err=True)
        raise typer.Exit(1)

    active_config = get_configuration(profile=profile)
    formatter = resolve_formatter(flag=output_format, active_config=active_config, command="organizations update")
    handlers.update_organization(
        org_id=org_id,
        name=name,
        active_config=active_config,
        formatter=formatter,
    )


@app.command(name="delete", short_help="Deletes an organization.")
def delete_organization(
    org_id: Annotated[
        str,
        typer.Option("--id", help="Unique identifier for the organization.", show_default=False),
    ],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompt."),
    ] = False,
    profile: Annotated[
        str,
        typer.Option(help="Name of the profile to use for remote server communication."),
    ] = "",
    output_format: Annotated[
        OutputFormatFieldsEnum | None,
        typer.Option("--format"),
    ] = None,
):
    if not yes:
        if not sys.stdin.isatty():
            typer.echo("Error: Use --yes to confirm deletion in non-interactive mode.", err=True)
            raise typer.Exit(1)
        confirmed = typer.confirm(f"Delete organization {org_id}?", default=False)
        if not confirmed:
            typer.echo("Aborted.")
            raise typer.Exit(0)

    active_config = get_configuration(profile=profile)
    formatter = resolve_formatter(flag=output_format, active_config=active_config, command="organizations delete")
    handlers.delete_organization(
        org_id=org_id,
        active_config=active_config,
        formatter=formatter,
    )


@users_app.command(name="list", short_help="Lists users in an organization.")
def list_users(
    org_id: Annotated[
        str,
        typer.Option("--id", help="Organization id.", show_default=False),
    ],
    profile: Annotated[
        str,
        typer.Option(help="Name of the profile to use for remote server communication."),
    ] = "",
    output_format: Annotated[
        OutputFormatFieldsEnum | None,
        typer.Option("--format"),
    ] = None,
):
    active_config = get_configuration(profile=profile)
    formatter = resolve_formatter(flag=output_format, active_config=active_config, command="organizations users list")
    handlers.list_organization_users(
        org_id=org_id,
        active_config=active_config,
        formatter=formatter,
    )


@users_app.command(name="add", short_help="Adds a user to an organization.")
def add_user(
    org_id: Annotated[
        str,
        typer.Option("--id", help="Organization id.", show_default=False),
    ],
    user: Annotated[
        str,
        typer.Option(help="User id to add.", show_default=False),
    ],
    profile: Annotated[
        str,
        typer.Option(help="Name of the profile to use for remote server communication."),
    ] = "",
    output_format: Annotated[
        OutputFormatFieldsEnum | None,
        typer.Option("--format"),
    ] = None,
):
    active_config = get_configuration(profile=profile)
    formatter = resolve_formatter(flag=output_format, active_config=active_config, command="organizations users add")
    handlers.add_organization_user(
        org_id=org_id,
        user_id=user,
        active_config=active_config,
        formatter=formatter,
    )


app.add_typer(users_app, name="users")
