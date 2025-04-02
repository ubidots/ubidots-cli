import re
from pathlib import Path

import httpx
import typer
import yaml

from cli.commons.enums import MessageColorEnum
from cli.commons.validators import is_valid_object_id
from cli.config.models import ProfileConfigModel


def build_endpoint(
    route: str,
    active_config: ProfileConfigModel,
    query_params: dict | None = None,
    **kwargs,
) -> tuple[str, dict]:
    url = f"{active_config.api_domain}{route.format(**kwargs)}"
    if query_params:
        filter_string = query_params.pop("filter", None)
        query_string = "&".join(
            f"{key}={value}" for key, value in query_params.items() if value is not None
        )
        url += f"?{query_string}"

        if filter_string:
            url += f"&{filter_string}"

    headers = {active_config.auth_method: active_config.access_token}
    return url, headers


def check_response_status(response: httpx.Response, custom_message: str | None = None):
    if response.status_code not in [httpx.codes.OK, httpx.codes.ACCEPTED]:
        response_json = response.json()
        error_message = response_json.get("detail") or response_json.get(
            "message", "Unknown error"
        )
        raise httpx.RequestError(
            f"{error_message} {custom_message}" if custom_message else error_message
        )


def get_instance_key(id: str | None = None, label: str | None = None) -> str:
    if isinstance(id, str):
        if is_valid_object_id(key=id):
            return id
        error_message = "'--id' is not a valid object id"
        raise typer.BadParameter(error_message)
    if isinstance(label, str):
        return f"~{label}"
    error_message = "Providing an '--id' or '--label' is required."
    raise typer.BadParameter(error_message)


def exit_with_error_message(exception: Exception, message: str = "", hint: str = ""):
    message = message if message else str(exception)
    typer.echo(
        typer.style(
            text=f"\n> [ERROR]: {message}\n",
            fg=MessageColorEnum.ERROR,
            bold=True,
        )
    )
    if hint:
        typer.echo(
            typer.style(
                text=f"[HINT]: {hint}\n",
                fg=MessageColorEnum.HINT,
                bold=True,
            )
        )
    raise typer.Exit(1) from exception


def exit_with_success_message(message: str = "Operation completed successfully."):
    typer.echo(
        typer.style(
            text=f"\n> [DONE]: {message}\n",
            fg=MessageColorEnum.SUCCESS,
            bold=True,
        )
    )
    raise typer.Exit(0)


def sanitize_function_name(name: str) -> str:
    return re.sub(
        r"^[^a-z0-9]+",
        "",
        re.sub(r"[^a-z0-9:._-]", "", re.sub(r"\s+", "-", name.strip().lower())),
    )


def load_yaml(file_path: str | Path) -> dict:
    file_path = Path(file_path)

    try:
        if not file_path.exists():
            error_message = f"File '{file_path}' not found"
            exit_with_error_message(
                exception=FileNotFoundError(error_message),
                message=error_message,
            )

        with file_path.open("r") as f:
            content = f.read().strip()
            if not content:
                error_message = f"File {file_path} is empty or not valid YAML"
                exit_with_error_message(
                    exception=ValueError(error_message),
                    message=error_message,
                )

            parsed_data = yaml.safe_load(content)

            if not isinstance(parsed_data, dict):
                error_message = f"Invalid YAML format in {file_path}"
                exit_with_error_message(
                    exception=ValueError(error_message),
                    message=error_message,
                )

            return parsed_data

    except yaml.YAMLError as e:
        error_message = f"Error parsing YAML file {file_path}: {e}"
        exit_with_error_message(
            exception=ValueError(error_message),
            message=error_message,
        )
    exception_message = "Unexpected error occurred while loading YAML file."
    raise AssertionError(exception_message)
