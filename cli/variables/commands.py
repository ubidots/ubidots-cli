from typing import Annotated
from typing import no_type_check

import typer

from cli.commons.enums import DefaultInstanceFieldEnum
from cli.commons.utils import get_instance_key
from cli.commons.utils import simple_lookup_key
from cli.variables import handlers
from cli.variables.enums import VariableTypeEnum

app = typer.Typer(help="Variable management and operations.")
DEFAULT_FIELDS = DefaultInstanceFieldEnum.fields()


@app.command(short_help="Retrieves a specific variable using its id.")
@simple_lookup_key(entity_name="variable")
@no_type_check
def get(
    id: str,
    fields: Annotated[
        list[str],
        typer.Option(
            help="Comma-separated fields to process. e.g. field1,field2,field3"
        ),
    ] = DEFAULT_FIELDS,
):
    variable_key = get_instance_key(id=id)
    handlers.retrieve_variable(variable_key=variable_key, fields=fields)


@app.command(short_help="Lists all available variables.")
@no_type_check
def list(
    fields: Annotated[
        list[str],
        typer.Option(
            help="Comma-separated fields to process. e.g. field1,field2,field3"
        ),
    ] = DEFAULT_FIELDS,
):
    handlers.list_variable(fields=fields)


@app.command(short_help="Adds a new variable.")
def add(
    device: Annotated[
        str,
        typer.Argument(
            help="The device associated with the variable. Its id or ['~label'|\\~label]."
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
    syntheticExpression: Annotated[
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
        syntheticExpression=syntheticExpression,
        tags=tags,
    )


@app.command(short_help="Deletes a specific variable using its id")
@simple_lookup_key(entity_name="variable")
def delete(id: str):
    variable_key = get_instance_key(id=id)
    handlers.delete_variable(variable_key=variable_key)
