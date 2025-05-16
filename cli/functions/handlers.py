import json

import httpx
import typer

from cli.commons.enums import OutputFormatFieldsEnum
from cli.commons.styles import print_colored_table
from cli.commons.utils import build_endpoint
from cli.config.models import ProfileConfigModel
from cli.functions import FUNCTION_API_ROUTES
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.exceptions import RemoteFunctionNotFoundError
from cli.functions.helpers import build_functions_payload
from cli.settings import settings


def list_functions(
    url: str,
    headers: dict,
    format: OutputFormatFieldsEnum,
):
    response = httpx.get(url, headers=headers)
    if format == OutputFormatFieldsEnum.JSON:
        typer.echo(json.dumps(response.json()["results"]))
    else:
        print_colored_table(results=response.json()["results"])


def retrieve_function(url: str, headers: dict, format: OutputFormatFieldsEnum):
    response = httpx.get(url, headers=headers)
    if format == OutputFormatFieldsEnum.JSON:
        typer.echo(json.dumps(response.json()))
    else:
        print_colored_table(results=[response.json()])
    return response


def update_function(url: str, headers: dict, data: dict, function_key: str):
    try:
        response = httpx.patch(url, headers=headers, json=data)
        response.raise_for_status()
        return response
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise RemoteFunctionNotFoundError(function_id=function_key) from exc
        raise
    except httpx.RequestError as exc:
        raise exc from None


def add_function(active_config: ProfileConfigModel, **kwargs):
    data = build_functions_payload(**kwargs)
    url, headers = build_endpoint(
        route=FUNCTION_API_ROUTES["base"],
        active_config=active_config,
    )
    client = httpx.Client(follow_redirects=True)

    response = client.post(url, headers=headers, json=data)
    response_json = response.json()

    if response.status_code != httpx.codes.CREATED:
        return {
            "success": False,
            "error": httpx.HTTPStatusError(
                message=response._content.decode("utf-8"),
                request=response.request,
                response=response,
            ),
        }

    runtime = data["serverless"]["runtime"]
    language = FunctionLanguageEnum.get_language_by_runtime(runtime)
    zip_path = settings.FUNCTIONS.TEMPLATES_PATH / f"{language}.zip"

    try:
        with open(zip_path, "rb") as zip_ref:
            zip_file = zip_ref.read()
    except FileNotFoundError as e:
        return {"success": False, "error": e}

    url, headers = build_endpoint(
        route=FUNCTION_API_ROUTES["zip_file"],
        function_key=response_json["id"],
        active_config=active_config,
    )
    files = {
        "zipFile": (
            "function_file_code.zip",
            zip_file,
            "application/zip",
        )
    }

    response = client.post(url=url, headers=headers, files=files)

    if (
        response.status_code != httpx.codes.OK
        and response.status_code != httpx.codes.ACCEPTED
    ):
        return {
            "success": False,
            "error": httpx.HTTPStatusError(
                message=response._content.decode("utf-8"),
                request=response.request,
                response=response,
            ),
        }

    return {
        "success": True,
        "function_id": response_json["id"],
        "label": response_json["label"],
    }


def delete_function(url: str, headers: dict, function_key: str):
    try:
        response = httpx.delete(url, headers=headers)
        if response.status_code == 404:
            raise httpx.HTTPStatusError(
                message=f"Function with id={function_key} not found.",
                request=response.request,
                response=response,
            )
        response.raise_for_status()
        return response
    except httpx.RequestError as exc:
        raise exc from None
    except httpx.HTTPStatusError as exc:
        raise exc from None
