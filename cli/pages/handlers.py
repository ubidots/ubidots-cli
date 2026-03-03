import json
from typing import TypedDict

import httpx
import typer

from cli.commons.enums import OutputFormatFieldsEnum
from cli.commons.styles import print_colored_table
from cli.commons.utils import build_endpoint
from cli.config.models import ProfileConfigModel
from cli.pages.constants import PAGE_API_ROUTES


class AddPagePayload(TypedDict):
    name: str
    label: str


def list_pages(
    url: str,
    headers: dict,
    format: OutputFormatFieldsEnum,
):
    response = httpx.get(url, headers=headers)
    response.raise_for_status()
    results = response.json().get("results", [])
    if format == OutputFormatFieldsEnum.JSON:
        typer.echo(json.dumps(results))
    else:
        print_colored_table(results=results)


def retrieve_page(url: str, headers: dict, format: OutputFormatFieldsEnum):
    response = httpx.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    if format == OutputFormatFieldsEnum.JSON:
        typer.echo(json.dumps(data))
    else:
        print_colored_table(results=[data])
    return response


def add_page(active_config: ProfileConfigModel, name: str, label: str):
    url, headers = build_endpoint(
        route=PAGE_API_ROUTES["base"],
        active_config=active_config,
    )
    data: AddPagePayload = {"name": name, "label": label}
    client = httpx.Client(follow_redirects=True)
    return client.post(url, headers=headers, json=data)


def delete_page(url: str, headers: dict, page_key: str):
    try:
        response = httpx.delete(url, headers=headers)
        if response.status_code == 404:
            raise httpx.HTTPStatusError(
                message=f"Page with id={page_key} not found.",
                request=response.request,
                response=response,
            )
        response.raise_for_status()
        return response
    except (httpx.RequestError, httpx.HTTPStatusError) as error:
        raise error


def upload_page_code(url: str, headers: dict, zip_file: bytes, page_name: str):
    files = {
        "zipFile": (
            f"{page_name}.zip",
            zip_file,
            "application/zip",
        )
    }
    client = httpx.Client(follow_redirects=True)
    return client.post(url=url, headers=headers, files=files)


def download_page_code(url: str, headers: dict):
    return httpx.get(url, headers=headers, follow_redirects=True)
