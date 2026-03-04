import httpx

from cli.commons.utils import build_endpoint
from cli.config.models import ProfileConfigModel
from cli.pages.constants import PAGE_API_ROUTES
from cli.pages.models import AddPagePayload



def add_page(active_config: ProfileConfigModel, name: str, label: str):
    url, headers = build_endpoint(
        route=PAGE_API_ROUTES["base"],
        active_config=active_config,
    )
    data: AddPagePayload = {"name": name, "label": label}
    client = httpx.Client(follow_redirects=True)
    return client.post(url, headers=headers, json=data)



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


