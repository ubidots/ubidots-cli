from functools import wraps
from typing import Annotated

import typer

from cli.commons.enums import BoolValuesEnum
from cli.commons.enums import MessageColorEnum
from cli.commons.validators import is_valid_object_id
from cli.config.helpers import read_cli_configuration


def build_endpoint(route: str, query_params: dict | None = None, **kwargs) -> str:
    access_config = read_cli_configuration()
    url = f"{access_config.api_domain}{route.format(**kwargs)}"
    if query_params:
        query_string = "&".join(f"{key}={value}" for key, value in query_params.items())
        url += f"?{query_string}"

    headers = {access_config.auth_method: access_config.access_token}
    return url, headers


def get_instance_key(id: str | None = None, label: str | None = None) -> str | None:
    if isinstance(id, str):
        if is_valid_object_id(key=id):
            return id
        error_message = "'--id' is not a valid object id"
        raise typer.BadParameter(error_message)
    if isinstance(label, str):
        return f"~{label}"
    error_message = "Providing an '--id' or '--label' is required."
    raise typer.BadParameter(error_message)


def simple_lookup_key(entity_name: str):
    def decorator(command_func):
        @wraps(command_func)
        def wrapper(*args, **kwargs):
            return command_func(*args, **kwargs)

        wrapper.__annotations__["id"] = Annotated[
            str,
            typer.Option(
                help=f"Unique identifier for the {entity_name}.", show_default=False
            ),
        ]
        wrapper.__annotations__["label"] = Annotated[
            str,
            typer.Option(
                help=f"Descriptive label for the {entity_name}.", show_default=False
            ),
        ]
        return wrapper

    return decorator


def exit_with_error_message(exception: Exception, message: str = ""):
    message = message if message else exception
    typer.echo(
        typer.style(
            text=f"\n> {message}\n",
            fg=MessageColorEnum.ERROR,
            bold=True,
        )
    )
    raise typer.Exit(1) from exception


def exit_with_success_message(message: str = "Operation completed successfully."):
    typer.echo(
        typer.style(
            text=f"\n> {message}\n",
            fg=MessageColorEnum.SUCCESS,
            bold=True,
        )
    )
    raise typer.Exit(0)


def str_to_bool(value: str) -> bool:
    val_lower = value.lower()
    for bool_value in BoolValuesEnum:
        if val_lower in bool_value.value:
            return bool_value == BoolValuesEnum.TRUE
    error_message = f"The value '{value}' cannot be interpreted as a boolean."
    raise ValueError(error_message)
