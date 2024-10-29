from functools import wraps
from typing import Annotated

import typer

from cli.commons.enums import EntityNameEnum


def simple_lookup_key(entity_name: str):
    def decorator(command_func):
        @wraps(command_func)
        def wrapper(*args, **kwargs):
            return command_func(*args, **kwargs)

        id_help_suffix = (
            "If both id and label are provided, the id takes precedence."
            if entity_name != EntityNameEnum.VARIABLE
            else ""
        )
        label_help_suffix = (
            "Ignored if id is provided."
            if entity_name != EntityNameEnum.VARIABLE
            else ""
        )

        id_help = f"Unique **identifier** for the {entity_name}. {id_help_suffix}"
        label_help = f"Descriptive label **identifier** for the {entity_name}. {label_help_suffix}"

        wrapper.__annotations__["id"] = Annotated[
            str,
            typer.Option(
                help=id_help,
                show_default=False,
            ),
        ]
        wrapper.__annotations__["label"] = Annotated[
            str,
            typer.Option(
                help=label_help,
                show_default=False,
            ),
        ]
        return wrapper

    return decorator


def add_verbose_option():
    def decorator(command_func):
        @wraps(command_func)
        def wrapper(*args, **kwargs):
            return command_func(*args, **kwargs)

        wrapper.__annotations__["verbose"] = Annotated[
            bool, typer.Option("--verbose", "-v", help="Enable verbose output.")
        ]
        return wrapper

    return decorator


def add_pagination_options():
    def decorator(command_func):
        @wraps(command_func)
        def wrapper(*args, **kwargs):
            return command_func(*args, **kwargs)

        wrapper.__annotations__["page_size"] = Annotated[
            int,
            typer.Option(
                help="Defines the page number to be retrieved.", show_default=False
            ),
        ]
        wrapper.__annotations__["page"] = Annotated[
            int,
            typer.Option(
                help="Defines how many items per page are retrieved.",
                show_default=False,
            ),
        ]
        return wrapper

    return decorator


def add_sort_by_option():
    def decorator(command_func):
        @wraps(command_func)
        def wrapper(*args, **kwargs):
            return command_func(*args, **kwargs)

        wrapper.__annotations__["sort_by"] = Annotated[
            str,
            typer.Option(
                help="Attribute to sort the result set by.", show_default=False
            ),
        ]
        return wrapper

    return decorator


def add_filter_option():
    def decorator(command_func):
        @wraps(command_func)
        def wrapper(*args, **kwargs):
            return command_func(*args, **kwargs)

        wrapper.__annotations__["filter"] = Annotated[
            str,
            typer.Option(
                help=(
                    "Filter results by attributes. "
                    "e.g. 'key1=val1&key2__in=val20,val21' or key1=val1\\&key2__in=val20,val21"
                ),
                show_default=False,
            ),
        ]
        return wrapper

    return decorator
