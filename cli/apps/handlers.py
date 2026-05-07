from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from cli.apps.constants import APPS_API_ROUTES
from cli.commons.utils import build_endpoint

if TYPE_CHECKING:
    from cli.apps.models import SetMenuPayload
    from cli.config.models import ProfileConfigModel


def list_apps(
    active_config: ProfileConfigModel,
    fields: str | None = None,
    filter: str | None = None,
    sort_by: str | None = None,
    page_size: int | None = None,
    page: int | None = None,
):
    url, headers = build_endpoint(
        route=APPS_API_ROUTES["base"],
        active_config=active_config,
        query_params={
            "fields": fields,
            "filter": filter,
            "sort_by": sort_by,
            "page_size": page_size,
            "page": page,
        },
    )
    with httpx.Client(follow_redirects=True) as client:
        return client.get(url, headers=headers)


def get_menu(active_config: ProfileConfigModel, app_key: str):
    url, headers = build_endpoint(
        route=APPS_API_ROUTES["menu"],
        app_key=app_key,
        active_config=active_config,
    )
    with httpx.Client(follow_redirects=True) as client:
        return client.get(url, headers=headers)


def set_menu(
    active_config: ProfileConfigModel,
    app_key: str,
    payload: SetMenuPayload,
):
    url, headers = build_endpoint(
        route=APPS_API_ROUTES["menu"],
        app_key=app_key,
        active_config=active_config,
    )
    with httpx.Client(follow_redirects=True) as client:
        return client.put(url, headers=headers, json=dict(payload))


def reset_menu(active_config: ProfileConfigModel, app_key: str):
    url, headers = build_endpoint(
        route=APPS_API_ROUTES["menu"],
        app_key=app_key,
        active_config=active_config,
    )
    with httpx.Client(follow_redirects=True) as client:
        return client.delete(url, headers=headers)
