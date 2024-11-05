import httpx
import typer

from cli.commons.enums import MessageColorEnum
from cli.commons.validators import is_valid_object_id
from cli.config.helpers import read_cli_configuration


def build_endpoint(
    route: str, query_params: dict | None = None, **kwargs
) -> tuple[str, dict]:
    access_config = read_cli_configuration()
    url = f"{access_config.api_domain}{route.format(**kwargs)}"
    if query_params:
        filter_string = query_params.pop("filter", None)
        query_string = "&".join(
            f"{key}={value}" for key, value in query_params.items() if value is not None
        )
        url += f"?{query_string}"

        if filter_string:
            url += f"&{filter_string}"

    headers = {access_config.auth_method: access_config.access_token}
    return url, headers


def check_response_status(response: httpx.Response):
    if response.status_code not in [httpx.codes.OK, httpx.codes.ACCEPTED]:
        response_json = response.json()
        error_message = response_json.get("detail") or response_json.get(
            "message", "Unknown error"
        )
        raise httpx.RequestError(error_message)


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
