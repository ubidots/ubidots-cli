import json

import httpx
import typer

from cli.commons.enums import OutputFormatFieldsEnum
from cli.commons.styles import print_colored_table
from cli.commons.utils import build_endpoint
from cli.commons.utils import exit_with_error_message
from cli.commons.utils import exit_with_success_message
from cli.functions import FUNCTION_API_ROUTES
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.helpers import build_functions_payload
from cli.settings import settings


def list_functions(
    fields: str,
    filter: str,
    sort_by: str,
    page_size: int,
    page: int,
    format: OutputFormatFieldsEnum,
):
    url, headers = build_endpoint(
        route=FUNCTION_API_ROUTES["base"],
        query_params={
            "fields": fields,
            "filter": filter,
            "sort_by": sort_by,
            "page_size": page_size,
            "page": page,
        },
    )
    response = httpx.get(url, headers=headers)
    if format == OutputFormatFieldsEnum.JSON:
        typer.echo(json.dumps(response.json()["results"]))
    else:
        print_colored_table(results=response.json()["results"])


def retrieve_function(function_key: str, fields: str, format: OutputFormatFieldsEnum):
    url, headers = build_endpoint(
        route=FUNCTION_API_ROUTES["detail"],
        function_key=function_key,
        query_params={"fields": fields},
    )
    response = httpx.get(url, headers=headers)
    if format == OutputFormatFieldsEnum.JSON:
        typer.echo(json.dumps(response.json()))
    else:
        print_colored_table(results=[response.json()])


def add_function(**kwargs):
    data = build_functions_payload(**kwargs)
    url, headers = build_endpoint(
        route=FUNCTION_API_ROUTES["base"],
    )
    client = httpx.Client(follow_redirects=True)
    response = client.post(url, headers=headers, json=data)
    response_json = response.json()
    if response.status_code != httpx.codes.CREATED:
        exit_with_error_message(
            httpx.HTTPStatusError(
                message=response._content.decode("utf-8"),
                request=response.request,
                response=response,
            )
        )

    runtime = data["serverless"]["runtime"]
    language = FunctionLanguageEnum.get_language_by_runtime(runtime)
    zip_path = settings.FUNCTIONS.TEMPLATES_PATH / f"{language}.zip"
    with open(zip_path, "rb") as zip_ref:
        zip_file = zip_ref.read()

    url, headers = build_endpoint(
        route=FUNCTION_API_ROUTES["zip_file"],
        function_key=response_json["id"],
    )
    files = {
        "zipFile": (
            "function_file_code.zip",
            zip_file,
            "application/zip",
        )
    }

    response = client.post(url=url, headers=headers, files=files)
    if response.status_code != httpx.codes.OK:
        exit_with_error_message(
            httpx.HTTPStatusError(
                message=response._content.decode("utf-8"),
                request=response.request,
                response=response,
            )
        )

    exit_with_success_message(
        f"The function with 'id={response_json['id']}' and "
        f"'label={response_json['label']}' was created successfully."
    )


def update_function(function_key: str, **kwargs):
    data = build_functions_payload(**kwargs)
    url, headers = build_endpoint(
        route=FUNCTION_API_ROUTES["detail"],
        function_key=function_key,
    )
    response = httpx.patch(url, headers=headers, json=data)
    if response.status_code == httpx.codes.OK:
        exit_with_success_message(
            f"The function with 'id={response.json()['id']}' and 'label={response.json()['label']}' "
            "was updated successfully."
        )
    else:
        exit_with_error_message(
            httpx.HTTPStatusError(
                message=response._content.decode("utf-8"),
                request=response.request,
                response=response,
            )
        )


def delete_function(function_key: str):
    url, headers = build_endpoint(
        route=FUNCTION_API_ROUTES["detail"],
        function_key=function_key,
    )
    httpx.delete(url, headers=headers)
    exit_with_success_message(
        f"The function '{function_key}' was removed successfully."
    )
