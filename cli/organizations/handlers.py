import httpx
import typer

from cli.commons.endpoint import build_endpoint
from cli.commons.formatters import OutputFormatter
from cli.config.models import ProfileConfigModel
from cli.organizations.constants import ORG_DETAIL_ROUTE
from cli.organizations.constants import ORG_LIST_ROUTE

REQUEST_TIMEOUT = 30.0


def list_organizations(
    fields: str,
    page_size: int | None,
    page: int | None,
    formatter: OutputFormatter,
    active_config: ProfileConfigModel,
) -> None:
    url, headers = build_endpoint(
        route=ORG_LIST_ROUTE,
        query_params={
            "fields": fields,
            "page_size": page_size,
            "page": page,
        },
        active_config=active_config,
    )
    response = httpx.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    if response.status_code == httpx.codes.OK:
        data = response.json()
        formatter.emit_results(data.get("results", data) if isinstance(data, dict) else data)
    else:
        formatter.emit_error(
            httpx.HTTPStatusError(
                message=response._content.decode("utf-8"),
                request=response.request,
                response=response,
            )
        )


def get_organization(
    org_id: str,
    formatter: OutputFormatter,
    active_config: ProfileConfigModel,
) -> None:
    url, headers = build_endpoint(
        route=ORG_DETAIL_ROUTE,
        org_id=org_id,
        active_config=active_config,
    )
    response = httpx.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    if response.status_code == httpx.codes.OK:
        formatter.emit_results(response.json())
    elif response.status_code == httpx.codes.NOT_FOUND:
        typer.echo(f"Organization not found: {org_id}", err=True)
        raise typer.Exit(4)
    else:
        formatter.emit_error(
            httpx.HTTPStatusError(
                message=response._content.decode("utf-8"),
                request=response.request,
                response=response,
            )
        )


def create_organization(
    name: str,
    formatter: OutputFormatter,
    active_config: ProfileConfigModel,
) -> None:
    url, headers = build_endpoint(
        route=ORG_LIST_ROUTE,
        active_config=active_config,
    )
    response = httpx.post(url, headers=headers, json={"name": name}, timeout=REQUEST_TIMEOUT)
    if response.status_code in {httpx.codes.OK, httpx.codes.CREATED}:
        formatter.emit_results(response.json())
    else:
        formatter.emit_error(
            httpx.HTTPStatusError(
                message=response._content.decode("utf-8"),
                request=response.request,
                response=response,
            )
        )


def update_organization(
    org_id: str,
    name: str | None,
    label: str | None,
    description: str | None,
    is_active: bool | None,
    app_key: str | None,
    properties: dict | None,
    formatter: OutputFormatter,
    active_config: ProfileConfigModel,
) -> None:
    url, headers = build_endpoint(
        route=ORG_DETAIL_ROUTE,
        org_id=org_id,
        active_config=active_config,
    )
    payload: dict = {}
    if name is not None:
        payload["name"] = name
    if label is not None:
        payload["label"] = label
    if description is not None:
        payload["description"] = description
    if is_active is not None:
        payload["isActive"] = is_active
    if app_key is not None:
        payload["app"] = app_key
    if properties is not None:
        payload["properties"] = properties

    response = httpx.patch(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
    if response.status_code == httpx.codes.OK:
        formatter.emit_results(response.json())
    elif response.status_code == httpx.codes.NOT_FOUND:
        typer.echo(f"Organization not found: {org_id}", err=True)
        raise typer.Exit(4)
    else:
        formatter.emit_error(
            httpx.HTTPStatusError(
                message=response._content.decode("utf-8"),
                request=response.request,
                response=response,
            )
        )


def delete_organization(
    org_id: str,
    formatter: OutputFormatter,
    active_config: ProfileConfigModel,
) -> None:
    url, headers = build_endpoint(
        route=ORG_DETAIL_ROUTE,
        org_id=org_id,
        active_config=active_config,
    )
    response = httpx.delete(url, headers=headers, timeout=REQUEST_TIMEOUT)
    if response.status_code in {httpx.codes.OK, httpx.codes.NO_CONTENT}:
        formatter.emit_success(f"Organization {org_id} deleted.")
    elif response.status_code == httpx.codes.NOT_FOUND:
        typer.echo(f"Organization not found: {org_id}", err=True)
        raise typer.Exit(4)
    else:
        formatter.emit_error(
            httpx.HTTPStatusError(
                message=response._content.decode("utf-8"),
                request=response.request,
                response=response,
            )
        )
