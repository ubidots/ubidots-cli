from typing import Annotated

import typer

from cli.commons.utils import get_instance_key
from cli.commons.utils import simple_lookup_key
from cli.variables import handlers
from cli.variables.enums import VariableTypeEnum

app = typer.Typer(help="Variable management and operations.")


@app.command(short_help="Lists all available variables.")
def list():
    handlers.list_variable()


@app.command(short_help="Retrieves a specific variable using its id.")
@simple_lookup_key(entity_name="variable")
def get(id: str):
    variable_key = get_instance_key(id=id)
    handlers.retrieve_variable(variable_key=variable_key)


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
    ] = VariableTypeEnum.RAW.value,
    unit: Annotated[
        str, typer.Option(help="The unit of measurement that represents the variable.")
    ] = "",
    syntheticExpression: Annotated[
        str,
        typer.Option(
            help=(
                f"If the variable is of type '{VariableTypeEnum.SYNTHETIC.value}', "
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
        type=type.value,
        unit=unit,
        syntheticExpression=syntheticExpression,
        tags=tags,
    )


@app.command(short_help="Deletes a specific variable using its id")
@simple_lookup_key(entity_name="variable")
def delete(id: str):
    variable_key = get_instance_key(id=id)
    handlers.delete_variable(variable_key=variable_key)
