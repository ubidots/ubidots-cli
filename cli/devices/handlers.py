import httpx
import typer

from cli.commons.styles import print_colored_table
from cli.commons.utils import build_endpoint


def list_devices(fields: list[str]):
    url, headers = build_endpoint(
        route="/api/v2.0/devices/",
        query_params={"fields": ",".join(fields)},
    )
    response = httpx.get(url, headers=headers)
    print_colored_table(results=response.json()["results"])


def retrieve_device(device_key: str, fields: list[str]):
    url, headers = build_endpoint(
        route="/api/v2.0/devices/{device_key}/",
        device_key=device_key,
        query_params={"fields": ",".join(fields)},
    )
    response = httpx.get(url, headers=headers)
    print_colored_table(results=[response.json()])


def add_device(**kwargs):
    data = {
        "label": kwargs.get("label"),
        "description": kwargs.get("description", ""),
        "organization": kwargs.get("organization") or None,
        "tags": kwargs.get("tags", "").split(",") if kwargs.get("tags") else [],
    }
    if name := kwargs.get("name"):
        data["name"] = name
    url, headers = build_endpoint(
        route="/api/v2.0/devices/",
    )
    client = httpx.Client(follow_redirects=True)
    response = client.post(url, headers=headers, data=data)
    typer.echo(
        f"The device with 'id={response.json()['id']}' and 'label={data['label']}' was created successfully."
    )


def delete_device(device_key: str):
    url, headers = build_endpoint(
        route="/api/v2.0/devices/{device_key}/",
        device_key=device_key,
    )
    httpx.delete(url, headers=headers)
    typer.echo(f"The device '{device_key}' was removed successfully.")
