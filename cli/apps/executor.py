from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import typer

from cli.apps import handlers
from cli.apps.enums import MenuAlignmentEnum
from cli.apps.enums import MenuModeEnum
from cli.apps.validators import read_bundled_default_menu
from cli.apps.validators import read_bundled_dtd
from cli.apps.validators import validate_menu_xml
from cli.commons.enums import OutputFormatFieldsEnum
from cli.commons.styles import print_colored_table
from cli.commons.utils import exit_with_error_message
from cli.commons.utils import exit_with_success_message

if TYPE_CHECKING:
    from cli.apps.models import SetMenuPayload
    from cli.config.models import ProfileConfigModel


def _exit_on_http_error(response: httpx.Response, message: str = "") -> None:
    if response.is_success:
        return
    try:
        body = response.json()
        detail = body.get("detail") or body.get("message") or response.text
    except (ValueError, AttributeError):
        detail = response.text or response.reason_phrase
    exit_with_error_message(
        exception=httpx.HTTPStatusError(
            message=detail,
            request=response.request,
            response=response,
        ),
        message=f"{response.status_code} {detail}{(' — ' + message) if message else ''}",
    )


def list_apps_cmd(
    active_config: ProfileConfigModel,
    fields: str,
    filter: str | None,
    sort_by: str | None,
    page_size: int | None,
    page: int | None,
    format: OutputFormatFieldsEnum,
):
    response = handlers.list_apps(
        active_config=active_config,
        fields=fields,
        filter=filter,
        sort_by=sort_by,
        page_size=page_size,
        page=page,
    )
    _exit_on_http_error(response)
    results = response.json().get("results", [])
    if format == OutputFormatFieldsEnum.JSON:
        typer.echo(json.dumps(results))
    else:
        print_colored_table(results=results)


def get_menu_cmd(
    active_config: ProfileConfigModel,
    app_key: str,
    format: OutputFormatFieldsEnum,
    output: str,
):
    response = handlers.get_menu(active_config=active_config, app_key=app_key)
    _exit_on_http_error(response)
    body = response.json()

    if output:
        Path(output).write_text(json.dumps(body, indent=2), encoding="utf-8")
        exit_with_success_message(f"Menu written to '{output}'.")
        return  # exit_with_success_message raises typer.Exit(0); explicit return makes the mutual exclusion structural.

    if format == OutputFormatFieldsEnum.JSON:
        typer.echo(json.dumps(body))
    else:
        typer.echo(body.get("menuXml", ""))


def _read_menu_xml(file_path: str) -> str:
    if file_path == "-":
        return sys.stdin.read()
    path = Path(file_path)
    if not path.exists():
        msg = f"File '{file_path}' not found."
        raise typer.BadParameter(msg)
    return path.read_text(encoding="utf-8")


def set_menu_cmd(
    active_config: ProfileConfigModel,
    app_key: str,
    file: str,
    alignment: MenuAlignmentEnum,
    mode: MenuModeEnum,
):
    xml = _read_menu_xml(file)
    validate_menu_xml(xml)
    payload: SetMenuPayload = {
        "menuMode": mode,
        "menuXml": xml,
        "menuAlignment": alignment,
    }
    response = handlers.set_menu(
        active_config=active_config,
        app_key=app_key,
        payload=payload,
    )
    _exit_on_http_error(response)
    exit_with_success_message(f"Menu updated for app '{app_key}'.")


def reset_menu_cmd(
    active_config: ProfileConfigModel,
    app_key: str,
    yes: bool,
):
    if not yes:
        typer.confirm(
            f"This deletes the custom menu for '{app_key}' and reverts to the platform default. Continue?",
            abort=True,
        )
    response = handlers.reset_menu(active_config=active_config, app_key=app_key)
    _exit_on_http_error(response)
    exit_with_success_message(f"Menu reset for app '{app_key}'.")


def default_menu_cmd(format: OutputFormatFieldsEnum):
    menu_xml = read_bundled_default_menu()
    if format == OutputFormatFieldsEnum.JSON:
        body = {
            "menuMode": "default",
            "menuXml": menu_xml,
            "menuAlignment": "left",
        }
        typer.echo(json.dumps(body))
    else:
        typer.echo(menu_xml)


def print_schema_cmd():
    typer.echo(read_bundled_dtd())
