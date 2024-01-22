from typing import Any

import requests
import typer

from cli.commons.enums import HTTPMethodEnum
from cli.commons.enums import RequestErrorEnum
from cli.config.helpers import read_cli_configuration


def build_endpoint(route: str, **kwargs) -> str:
    access_config = read_cli_configuration()
    url = f"{access_config.api_domain}{route.format(**kwargs)}"
    headers = {access_config.auth_method.value: access_config.access_token}
    return url, headers


def perform_http_request(
    method: HTTPMethodEnum, url: str, headers: dict[str, str], **kwargs: Any
) -> requests.Response:
    supported_methods = {
        HTTPMethodEnum.GET: requests.get,
        HTTPMethodEnum.POST: requests.post,
        HTTPMethodEnum.PATCH: requests.patch,
        HTTPMethodEnum.PUT: requests.put,
        HTTPMethodEnum.DELETE: requests.delete,
    }
    if method not in supported_methods:
        typer.echo(f"Unsupported HTTP method: {method}")
        raise typer.Exit(1)

    error_messages = {
        RequestErrorEnum.HTTP_ERROR: "HTTP error occurred.",
        RequestErrorEnum.CONNECTION_ERROR: "Connection error occurred.",
        RequestErrorEnum.TIMEOUT: "Timeout error occurred.",
        RequestErrorEnum.REQUEST_EXCEPTION: "Error during request.",
        RequestErrorEnum.UNKNOWN_ERROR: "Unknown error occurred.",
    }
    try:
        response = supported_methods[method](url, headers=headers, **kwargs)
        response.raise_for_status()
        return response
    except requests.RequestException as error:
        error_type = type(error).__name__
        if not error_type:
            error_type = RequestErrorEnum.UNKNOWN_ERROR
        error_message = error_messages.get(RequestErrorEnum(error_type))
        typer.echo(f"{error_message} {error}")
        raise typer.Exit(1) from error
