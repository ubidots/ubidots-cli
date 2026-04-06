from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from cli.commons.utils import build_endpoint
from cli.pages.constants import PAGE_API_ROUTES

if TYPE_CHECKING:
    from cli.config.models import ProfileConfigModel
    from cli.pages.models import AddPagePayload
    from cli.pages.models import UpdatePagePayload


def add_page(active_config: ProfileConfigModel, name: str, label: str):
    url, headers = build_endpoint(
        route=PAGE_API_ROUTES["base"],
        active_config=active_config,
    )
    data: AddPagePayload = {"name": name, "label": label}
    client = httpx.Client(follow_redirects=True)
    return client.post(url, headers=headers, json=data)


def update_page(
    active_config: ProfileConfigModel, page_key: str, name: str = "", label: str = ""
):
    url, headers = build_endpoint(
        route=PAGE_API_ROUTES["detail"],
        page_key=page_key,
        active_config=active_config,
    )
    data: UpdatePagePayload = {}
    if name:
        data["name"] = name
    if label:
        data["label"] = label
    client = httpx.Client(follow_redirects=True)
    return client.patch(url, headers=headers, json=data)


def upload_page_code(url: str, headers: dict, zip_file: bytes, page_name: str):
    files = {
        "zipFile": (
            f"{page_name}.zip",
            zip_file,
            "application/zip",
        )
    }
    client = httpx.Client(follow_redirects=True)
    return client.post(url=url, headers=headers, files=files)
