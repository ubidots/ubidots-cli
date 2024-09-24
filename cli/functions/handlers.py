import httpx

from cli.commons.styles import print_colored_table
from cli.commons.utils import build_endpoint
from cli.commons.utils import exit_with_error_message
from cli.commons.utils import exit_with_success_message
from cli.functions import FUNCTION_API_ROUTES


def list_functions(fields: str, filter: str, sort_by: str, page_size: int, page: int):
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
    print_colored_table(results=response.json()["results"])


def retrieve_function(function_key: str, fields: str):
    url, headers = build_endpoint(
        route=FUNCTION_API_ROUTES["detail"],
        function_key=function_key,
        query_params={"fields": fields},
    )
    response = httpx.get(url, headers=headers)
    print_colored_table(results=[response.json()])


def add_function(**kwargs):
    data = {
        "label": kwargs.get("label"),
        "triggers": kwargs.get("triggers", {}),
        "serverless": kwargs.get("serverless", {}),
        "environment": kwargs.get("environment", []),
    }
    if name := kwargs.get("name"):
        data["name"] = name
    url, headers = build_endpoint(
        route=FUNCTION_API_ROUTES["base"],
    )
    client = httpx.Client(follow_redirects=True)
    response = client.post(url, headers=headers, data=data)
    exit_with_success_message(
        f"The function with 'id={response.json()['id']}' and 'label={response.json()['label']}' was created successfully."
    )


def update_function(function_key: str, **kwargs):
    data = {}
    fields = ["label", "name", "triggers", "serverless", "environment"]
    for field in fields:
        if value := kwargs.get(field):
            data[field] = value

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
