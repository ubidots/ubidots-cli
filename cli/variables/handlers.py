import httpx

from cli.commons.styles import print_colored_table
from cli.commons.utils import build_endpoint
from cli.commons.utils import exit_with_success_message


def list_variable(fields: str, filter: str, sort_by: str, page_size: int, page: int):
    url, headers = build_endpoint(
        route="/api/v2.0/variables/",
        query_params={
            "fields": fields,
            "filter": filter,
            "sort_by": sort_by,
            "page_size": page_size,
            "page": page,
        },
    )
    response = httpx.get(url, headers=headers)
    print_colored_table(results=response.json()["results"])


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
        "properties": kwargs.get("properties", {}),
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
    exit_with_success_message(
        f"The variable with 'id={response.json()['id']}' and 'label={data['label']}' was created successfully "
        f"on device with 'device.id={response.json()['device']['id']}' "
        f"and 'device.label={response.json()['device']['label']}'."
    )


def update_variable(variable_key: str, **kwargs):
    data = dict(kwargs)
    if tags := data.get("tags"):
        data["tags"] = tags.split(",")

    url, headers = build_endpoint(
        route="/api/v2.0/variables/{variable_key}/",
        variable_key=variable_key,
    )
    response = httpx.patch(url, headers=headers, data=data)
    if response.status_code == httpx.codes.OK:
        exit_with_success_message(
            f"The variable with 'id={response.json()['id']}' and 'label={response.json()['label']}' "
            "was updated successfully."
        )


def delete_variable(variable_key: str):
    url, headers = build_endpoint(
        route="/api/v2.0/variables/{variable_key}/",
        variable_key=variable_key,
    )
    httpx.delete(url, headers=headers)
    exit_with_success_message(
        f"The variable '{variable_key}' was removed successfully."
    )
