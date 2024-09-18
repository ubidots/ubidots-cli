import httpx
import typer

from cli.commons.styles import print_colored_table
from cli.commons.utils import build_endpoint


def list_variable(fields: str, page_size: int, page: int):
    url, headers = build_endpoint(
        route="/api/v2.0/variables/",
        query_params={
            "fields": fields,
            "page_size": page_size,
            "page": page,
        },
    )
    response = httpx.get(url, headers=headers)
    print_colored_table(
        results=response.json()["results"],
    )


def retrieve_variable(variable_key: str, fields: str):
    url, headers = build_endpoint(
        route="/api/v2.0/variables/{variable_key}/",
        variable_key=variable_key,
        query_params={"fields": fields},
    )
    response = httpx.get(url, headers=headers)
    print_colored_table(results=[response.json()])


def add_variable(**kwargs):
    data = {
        "description": kwargs.get("description", ""),
        "device": kwargs.get("device") or None,
        "type": kwargs.get("type"),
        "unit": kwargs.get("unit") or None,
        "syntheticExpression": kwargs.get("syntheticExpression", ""),
        "tags": kwargs.get("tags", "").split(",") if kwargs.get("tags") else [],
    }
    if label := kwargs.get("label"):
        data["label"] = label
    if name := kwargs.get("name"):
        data["name"] = name
    url, headers = build_endpoint(
        route="/api/v2.0/variables/",
    )
    client = httpx.Client(follow_redirects=True)
    response = client.post(url, headers=headers, data=data)
    typer.echo(
        f"The variable with 'id={response.json()['id']}' and 'label={data['label']}' was created successfully "
        f"on device with 'device.id={response.json()['device']['id']}' "
        f"and 'device.label={response.json()['device']['label']}'."
    )


def delete_variable(variable_key: str):
    url, headers = build_endpoint(
        route="/api/v2.0/variables/{variable_key}/",
        variable_key=variable_key,
    )
    httpx.delete(url, headers=headers)
    typer.echo(f"The variable '{variable_key}' was removed successfully.")
