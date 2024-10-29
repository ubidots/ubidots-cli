from typing import Annotated
from typing import Optional
from typing import no_type_check

import typer

from cli.commons.decorators import add_filter_option
from cli.commons.decorators import add_pagination_options
from cli.commons.decorators import add_sort_by_option
from cli.commons.decorators import simple_lookup_key
from cli.commons.enums import DefaultInstanceFieldEnum
from cli.commons.enums import EntityNameEnum
from cli.commons.enums import OutputFormatFieldsEnum
from cli.commons.utils import get_instance_key
from cli.commons.validators import is_valid_json_string
from cli.settings import settings
from cli.variables import handlers
from cli.variables.enums import VariableTypeEnum

FIELDS_VARIABLE_HELP_TEXT = (
    "Comma-separated fields to process * e.g. field1,field2,field3. "
    "* Available fields: (id, label, name, createdAt, syntheticExpression, description, "
    "device, lastActivity, lastValue, properties, tags, type, unit, url, valuesUrl). "
    "For more details, visit the documentation at:\n"
    "https://docs.ubidots.com/reference/variable-object"
)

app = typer.Typer(help="Variable management and operations.")


@app.command(short_help="Deletes a specific variable using its id")
@simple_lookup_key(entity_name=EntityNameEnum.VARIABLE)
def delete(id: str):
    variable_key = get_instance_key(id=id)
    handlers.delete_variable(variable_key=variable_key)


@app.command(short_help="Retrieves a specific variable using its id.")
@simple_lookup_key(entity_name=EntityNameEnum.VARIABLE)
@no_type_check
def get(
    id: str,
    fields: Annotated[
        str,
        typer.Option(help=FIELDS_VARIABLE_HELP_TEXT),
    ] = DefaultInstanceFieldEnum.get_default_fields(),
    format: OutputFormatFieldsEnum = settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
):
    variable_key = get_instance_key(id=id)
    handlers.retrieve_variable(
        variable_key=variable_key,
        fields=fields,
        format=format,
    )


@app.command(short_help="Lists all available variables.")
@add_pagination_options()
@add_sort_by_option()
@add_filter_option()
@no_type_check
def list(
    fields: Annotated[
        str,
        typer.Option(help=FIELDS_VARIABLE_HELP_TEXT),
    ] = DefaultInstanceFieldEnum.get_default_fields(),
    filter: str | None = None,
    sort_by: str | None = None,
    page_size: int | None = None,
    page: int | None = None,
    format: OutputFormatFieldsEnum = settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
):
    handlers.list_variable(
        fields=fields,
        filter=filter,
        sort_by=sort_by,
        page_size=page_size,
        page=page,
        format=format,
    )


@app.command(short_help="Adds a new variable.")
def add(
    device: Annotated[
        str,
        typer.Argument(
            help="The device associated with the variable. Its id or ['~label'|\\~label].",
            show_default=False,
        ),
    ],
    label: Annotated[str, typer.Argument(help="The label for the variable.")] = "",
    name: Annotated[str, typer.Argument(help="The name of the variable.")] = "",
    description: Annotated[
        str, typer.Option(help="A brief description of the variable.")
    ] = "",
    type: Annotated[
        VariableTypeEnum,
        typer.Option(
            help="The type of variable.",
            show_choices=True,
            show_default=True,
        ),
    ] = VariableTypeEnum.RAW,
    unit: Annotated[
        str, typer.Option(help="The unit of measurement that represents the variable.")
    ] = "",
    synthetic_expression: Annotated[
        str,
        typer.Option(
            help=(
                f"If the variable is of type '{VariableTypeEnum.SYNTHETIC}', "
                "this is the corresponding synthetic expression used to calculate its value."
            )
        ),
    ] = "",
    tags: Annotated[
        str,
        typer.Option(help="Comma-separated tags for the variable. e.g. tag1,tag2,tag3"),
    ] = "",
    properties: Annotated[
        str,
        typer.Option(
            help="Device properties in JSON format.", callback=is_valid_json_string
        ),
    ] = "{}",
    min: Annotated[
        Optional[int],  # noqa: UP007
        typer.Option(
            help="Lowest value allowed.",
            show_default=False,
        ),
    ] = None,
    max: Annotated[
        Optional[int],  # noqa: UP007
        typer.Option(
            help="Highest value allowed.",
            show_default=False,
        ),
    ] = None,
):
    if not label and not name:
        error_message = "Either 'label' or 'name' must be provided."
        raise typer.BadParameter(error_message)

    handlers.add_variable(
        label=label,
        name=name,
        description=description,
        device=device,
        type=type,
        unit=unit,
        synthetic_expression=synthetic_expression,
        tags=tags,
        properties=properties,
        min=min,
        max=max,
    )


@app.command(short_help="Update a variable.")
@simple_lookup_key(entity_name=EntityNameEnum.VARIABLE)
def update(
    id: str,
    new_label: Annotated[str, typer.Option(help="The label for the variable.")] = "",
    new_name: Annotated[str, typer.Option(help="The name of the variable.")] = "",
    description: Annotated[
        str, typer.Option(help="A brief description of the variable.")
    ] = "",
    type: Annotated[
        VariableTypeEnum,
        typer.Option(
            help="The type of variable.",
            show_choices=True,
            show_default=True,
        ),
    ] = VariableTypeEnum.RAW,
    unit: Annotated[
        str, typer.Option(help="The unit of measurement that represents the variable.")
    ] = "",
    synthetic_expression: Annotated[
        str,
        typer.Option(
            help=(
                f"If the variable is of type '{VariableTypeEnum.SYNTHETIC}', "
                "this is the corresponding synthetic expression used to calculate its value."
            )
        ),
    ] = "",
    tags: Annotated[
        str,
        typer.Option(help="Comma-separated tags for the variable. e.g. tag1,tag2,tag3"),
    ] = "",
    properties: Annotated[
        str,
        typer.Option(
            help="Device properties in JSON format.", callback=is_valid_json_string
        ),
    ] = "{}",
    min: Annotated[
        Optional[int],  # noqa: UP007
        typer.Option(
            help="Lowest value allowed.",
            show_default=False,
        ),
    ] = None,
    max: Annotated[
        Optional[int],  # noqa: UP007
        typer.Option(
            help="Highest value allowed.",
            show_default=False,
        ),
    ] = None,
):

    variable_key = get_instance_key(id=id)
    handlers.update_variable(
        variable_key=variable_key,
        label=new_label,
        name=new_name,
        description=description,
        type=type,
        unit=unit,
        synthetic_expression=synthetic_expression,
        tags=tags,
        properties=properties,
        min=min,
        max=max,
    )
