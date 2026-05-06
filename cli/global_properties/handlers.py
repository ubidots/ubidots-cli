from __future__ import annotations

import json
from typing import TYPE_CHECKING

import httpx
import typer

from cli.commons.enums import OutputFormatFieldsEnum
from cli.commons.styles import print_colored_table
from cli.commons.utils import build_endpoint
from cli.commons.utils import exit_with_error_message
from cli.commons.utils import exit_with_success_message
from cli.global_properties.constants import GLOBAL_PROPERTIES_API_ROUTES

if TYPE_CHECKING:
    from cli.config.models import ProfileConfigModel


def _exit_on_error(response: httpx.Response) -> None:
    if response.status_code in (
        httpx.codes.OK,
        httpx.codes.CREATED,
        httpx.codes.NO_CONTENT,
    ):
        return
    exit_with_error_message(
        httpx.HTTPStatusError(
            message=(
                response._content.decode("utf-8")
                if response.content
                else response.reason_phrase
            ),
            request=response.request,
            response=response,
        )
    )


def list_properties(
    active_config: ProfileConfigModel,
    fields: str,
    search: str | None,
    sort_by: str | None,
    page_size: int | None,
    page: int | None,
    created_after: str | None,
    updated_after: str | None,
    output_format: OutputFormatFieldsEnum,
):
    query_params: dict = {
        "fields": fields,
        "search": search,
        "ordering": sort_by,
        "page_size": page_size,
        "page": page,
    }
    if created_after:
        query_params["created_at__gte"] = created_after
    if updated_after:
        query_params["updated_at__gte"] = updated_after

    url, headers = build_endpoint(
        route=GLOBAL_PROPERTIES_API_ROUTES["base"],
        active_config=active_config,
        query_params=query_params,
    )
    with httpx.Client(follow_redirects=True) as client:
        response = client.get(url, headers=headers)
    _exit_on_error(response)
    results = response.json().get("results", [])
    if output_format == OutputFormatFieldsEnum.JSON:
        typer.echo(json.dumps(results))
    else:
        print_colored_table(results=results)


def retrieve_property(
    active_config: ProfileConfigModel,
    property_key: str,
    fields: str,
    output_format: OutputFormatFieldsEnum,
):
    url, headers = build_endpoint(
        route=GLOBAL_PROPERTIES_API_ROUTES["detail"],
        property_key=property_key,
        active_config=active_config,
        query_params={"fields": fields},
    )
    with httpx.Client(follow_redirects=True) as client:
        response = client.get(url, headers=headers)
    _exit_on_error(response)
    body = response.json()
    if output_format == OutputFormatFieldsEnum.JSON:
        typer.echo(json.dumps(body))
    else:
        print_colored_table(results=[body])


def add_property(active_config: ProfileConfigModel, payload: dict):
    url, headers = build_endpoint(
        route=GLOBAL_PROPERTIES_API_ROUTES["base"],
        active_config=active_config,
    )
    with httpx.Client(follow_redirects=True) as client:
        response = client.post(url, headers=headers, json=payload)
    if response.status_code != httpx.codes.CREATED:
        _exit_on_error(response)
    body = response.json()
    exit_with_success_message(
        f"Global property with 'id={body.get('id')}' and 'label={body.get('label')}' was created successfully."
    )


def update_property(
    active_config: ProfileConfigModel, property_key: str, payload: dict
):
    if not payload:
        exit_with_success_message(f"No fields to update on '{property_key}'. Skipped.")
    url, headers = build_endpoint(
        route=GLOBAL_PROPERTIES_API_ROUTES["detail"],
        property_key=property_key,
        active_config=active_config,
    )
    with httpx.Client(follow_redirects=True) as client:
        response = client.patch(url, headers=headers, json=payload)
    if response.status_code != httpx.codes.OK:
        _exit_on_error(response)
    body = response.json()
    exit_with_success_message(
        f"Global property with 'id={body.get('id')}' and 'label={body.get('label')}' was updated successfully."
    )


def delete_property(active_config: ProfileConfigModel, property_key: str):
    url, headers = build_endpoint(
        route=GLOBAL_PROPERTIES_API_ROUTES["detail"],
        property_key=property_key,
        active_config=active_config,
    )
    with httpx.Client(follow_redirects=True) as client:
        response = client.delete(url, headers=headers)
    if response.status_code not in (httpx.codes.NO_CONTENT, httpx.codes.OK):
        _exit_on_error(response)
    exit_with_success_message(
        f"Global property '{property_key}' was removed successfully."
    )
