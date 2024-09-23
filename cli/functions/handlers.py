import httpx

from cli.commons.styles import print_colored_table
from cli.commons.utils import build_endpoint
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


def delete_function(function_key: str):
    url, headers = build_endpoint(
        route=FUNCTION_API_ROUTES["detail"],
        function_key=function_key,
    )
    httpx.delete(url, headers=headers)
    exit_with_success_message(
        f"The function '{function_key}' was removed successfully."
    )
