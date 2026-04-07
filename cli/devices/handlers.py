import httpx

from cli.commons.formatters import OutputFormatter
from cli.commons.utils import build_endpoint
from cli.config.models import ProfileConfigModel
from cli.devices.helpers import build_devices_payload


def list_devices(
    fields: str,
    filter: str,
    sort_by: str,
    page_size: int,
    page: int,
    formatter: OutputFormatter,
    active_config: ProfileConfigModel,
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
        active_config=active_config,
    )
    response = httpx.get(url, headers=headers)
    formatter.emit_results(response.json()["results"])


def retrieve_device(
    device_key: str,
    fields: str,
    formatter: OutputFormatter,
    active_config: ProfileConfigModel,
):
    url, headers = build_endpoint(
        route="/api/v2.0/devices/{device_key}/",
        device_key=device_key,
        query_params={"fields": fields},
        active_config=active_config,
    )
    response = httpx.get(url, headers=headers)
    formatter.emit_results(response.json())


def add_device(active_config: ProfileConfigModel, formatter: OutputFormatter, **kwargs):
    data = build_devices_payload(**kwargs)
    url, headers = build_endpoint(
        route="/api/v2.0/devices/", active_config=active_config
    )
    client = httpx.Client(follow_redirects=True)
    response = client.post(url, headers=headers, json=data)
    if response.status_code == httpx.codes.CREATED:
        formatter.emit_success(
            f"The device with 'id={response.json()['id']}' and 'label={data['label']}' was created successfully."
        )
    else:
        formatter.emit_error(
            httpx.HTTPStatusError(
                message=response._content.decode("utf-8"),
                request=response.request,
                response=response,
            )
        )


def update_device(device_key: str, active_config: ProfileConfigModel, formatter: OutputFormatter, **kwargs):
    data = build_devices_payload(**kwargs)
    url, headers = build_endpoint(
        route="/api/v2.0/devices/{device_key}/",
        device_key=device_key,
        active_config=active_config,
    )
    response = httpx.patch(url, headers=headers, json=data)
    if response.status_code == httpx.codes.OK:
        formatter.emit_success(
            f"The device with 'id={response.json()['id']}' and 'label={response.json()['label']}' "
            "was updated successfully."
        )
    else:
        formatter.emit_error(
            httpx.HTTPStatusError(
                message=response._content.decode("utf-8"),
                request=response.request,
                response=response,
            )
        )


def delete_device(device_key: str, active_config: ProfileConfigModel, formatter: OutputFormatter):
    url, headers = build_endpoint(
        route="/api/v2.0/devices/{device_key}/",
        device_key=device_key,
        active_config=active_config,
    )
    httpx.delete(url, headers=headers)
    formatter.emit_success(f"The device '{device_key}' was removed successfully.")
