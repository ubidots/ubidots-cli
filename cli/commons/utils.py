import time
from functools import wraps
from typing import Annotated
from typing import Any

import requests
import typer
from requests.exceptions import RequestException

from cli.commons.enums import BoolValuesEnum
from cli.commons.enums import HTTPMethodEnum
from cli.commons.enums import MessageColorEnum
from cli.commons.enums import RequestErrorEnum
from cli.commons.exceptions import HttpMaxAttemptsRequestException
from cli.commons.exceptions import HttpRequestException
from cli.commons.validators import is_valid_object_id
from cli.config.helpers import read_cli_configuration
from cli.settings import settings


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


def retry_on_failure(
    max_retries=settings.REQUESTS.RETRY_MAX_ATTEMPTS,
    initial_wait=settings.REQUESTS.RETRY_DELAY,
    backoff_factor=settings.REQUESTS.RETRY_BACKOFF_MULTIPLIER,
):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            wait = initial_wait
            last_exception = None
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except HttpRequestException as error:
                    last_exception = error
                    time.sleep(wait)
                    retries += 1
                    wait *= backoff_factor
            raise HttpMaxAttemptsRequestException(attemps=retries) from last_exception

        return wrapper

    return decorator


@retry_on_failure()
def perform_http_request(
    method: HTTPMethodEnum, url: str, **kwargs: Any
) -> requests.Response:
    supported_methods = {
        HTTPMethodEnum.GET: requests.get,
        HTTPMethodEnum.POST: requests.post,
        HTTPMethodEnum.PATCH: requests.patch,
        HTTPMethodEnum.PUT: requests.put,
        HTTPMethodEnum.DELETE: requests.delete,
    }
    error_messages = {
        RequestErrorEnum.HTTP_ERROR: "HTTP error occurred.",
        RequestErrorEnum.CONNECTION_ERROR: "Connection error occurred.",
        RequestErrorEnum.TIMEOUT: "Timeout error occurred.",
        RequestErrorEnum.REQUEST_EXCEPTION: "Error during request.",
        RequestErrorEnum.UNKNOWN_ERROR: "Unknown error occurred.",
    }
    try:
        response = supported_methods[method](url, **kwargs)
        response.raise_for_status()
        return response
    except RequestException as error:
        error_type = type(error).__name__
        if not error_type:
            error_type = RequestErrorEnum.UNKNOWN_ERROR
        error_message = error_messages.get(RequestErrorEnum(error_type))
        if hasattr(error.response, "content"):
            typer.echo(f"{error_message} {error.response.content}")
        raise HttpRequestException(message=error_message) from error


def show_error_and_exit(error: Exception):
    message = f"* {error}\n"
    typer.echo(
        typer.style(
            text=message,
            fg=MessageColorEnum.ERROR,
            bold=True,
        )
    )
    raise typer.Exit(1) from error


def str_to_bool(value: str) -> bool:
    val_lower = value.lower()
    for bool_value in BoolValuesEnum:
        if val_lower in bool_value.value:
            return bool_value == BoolValuesEnum.TRUE
    error_message = f"The value '{value}' cannot be interpreted as a boolean."
    raise ValueError(error_message)
