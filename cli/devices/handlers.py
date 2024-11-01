import json

import httpx
import typer

from cli.commons.enums import OutputFormatFieldsEnum
from cli.commons.styles import print_colored_table
from cli.commons.utils import build_endpoint
from cli.commons.utils import exit_with_error_message
from cli.commons.utils import exit_with_success_message
from cli.devices.helpers import build_devices_payload


def list_devices(
    fields: str,
    filter: str,
    sort_by: str,
    page_size: int,
    page: int,
    format: OutputFormatFieldsEnum,
):
    url, headers = build_endpoint(
        route="/api/v2.0/devices/",
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


def retrieve_device(device_key: str, fields: str, format: OutputFormatFieldsEnum):
    url, headers = build_endpoint(
        route="/api/v2.0/devices/{device_key}/",
        device_key=device_key,
        query_params={"fields": fields},
    )
    response = httpx.get(url, headers=headers)
    if format == OutputFormatFieldsEnum.JSON:
        typer.echo(json.dumps(response.json()))
    else:
        print_colored_table(results=[response.json()])


def add_device(**kwargs):
    data = build_devices_payload(**kwargs)
    url, headers = build_endpoint(
        route="/api/v2.0/devices/",
    )
    client = httpx.Client(follow_redirects=True)
    response = client.post(url, headers=headers, json=data)
    if response.status_code == httpx.codes.CREATED:
        exit_with_success_message(
            f"The device with 'id={response.json()['id']}' and 'label={data['label']}' was created successfully."
        )
    else:
        exit_with_error_message(
            httpx.HTTPStatusError(
                message=response._content.decode("utf-8"),
                request=response.request,
                response=response,
            )
        )


def update_device(device_key: str, **kwargs):
    data = build_devices_payload(**kwargs)
    url, headers = build_endpoint(
        route="/api/v2.0/devices/{device_key}/",
        device_key=device_key,
    )
    response = httpx.patch(url, headers=headers, json=data)
    if response.status_code == httpx.codes.OK:
        exit_with_success_message(
            f"The device with 'id={response.json()['id']}' and 'label={response.json()['label']}' "
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


def delete_device(device_key: str):
    url, headers = build_endpoint(
        route="/api/v2.0/devices/{device_key}/",
        device_key=device_key,
    )
    httpx.delete(url, headers=headers)
    exit_with_success_message(f"The device '{device_key}' was removed successfully.")
