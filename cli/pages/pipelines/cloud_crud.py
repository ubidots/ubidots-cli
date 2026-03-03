from dataclasses import dataclass
from pathlib import Path

import httpx
import typer

from cli.commons.enums import MessageColorEnum
from cli.commons.pipelines import PipelineStep
from cli.commons.utils import build_endpoint
from cli.pages.constants import PAGE_API_ROUTES
from cli.pages.handlers import add_page
from cli.pages.handlers import delete_page
from cli.pages.handlers import list_pages
from cli.pages.handlers import retrieve_page


@dataclass
class BuildPageEndpointStep(PipelineStep):
    api_route: str

    def execute(self, data):
        page_key = data.get("page_key") or data.get("remote_id")
        if not page_key:
            msg = "A 'page_key' or 'remote_id' is required to build the page endpoint."
            raise ValueError(msg)
        active_config = data["active_config"]
        url, headers = build_endpoint(
            route=self.api_route,
            page_key=page_key,
            active_config=active_config,
        )
        data["url"] = url
        data["headers"] = headers
        return data


class ListPagesFromRemoteServerStep(PipelineStep):
    def execute(self, data):
        active_config = data["active_config"]
        format = data["format"]
        fields = data.get("fields")
        page_size = data.get("page_size")
        page = data.get("page")
        sort_by = data.get("sort_by")
        url, headers = build_endpoint(
            route=PAGE_API_ROUTES["base"],
            active_config=active_config,
            query_params={
                "fields": fields,
                "sort_by": sort_by,
                "page_size": page_size,
                "page": page,
            },
        )
        list_pages(url, headers, format)
        return data


class GetPageFromRemoteServerStep(PipelineStep):
    def execute(self, data):
        page_key = data["page_key"]
        active_config = data["active_config"]
        format = data["format"]
        fields = data.get("fields")
        url, headers = build_endpoint(
            route=PAGE_API_ROUTES["detail"],
            page_key=page_key,
            active_config=active_config,
            query_params={"fields": fields},
        )
        retrieve_page(url=url, headers=headers, format=format)
        return data


class CreatePageRemoteServerStep(PipelineStep):
    def execute(self, data):
        active_config = data["active_config"]
        name = data["name"]
        label = data["label"]
        response = add_page(
            active_config=active_config,
            name=name,
            label=label,
        )
        if response.status_code not in (httpx.codes.OK, httpx.codes.CREATED):
            msg = f"Failed to create page: {response.text}"
            raise RuntimeError(msg)
        response_data = response.json()
        page_id = response_data.get("id", "")
        page_label = response_data.get("label", label)

        data["page_key"] = page_id
        data["page_id"] = page_id
        data["page_label"] = page_label
        data["page_name"] = name

        typer.echo(
            typer.style(
                text=f"\n> [DONE]: Page with id {page_id} and label {page_label} created successfully.",
                fg=MessageColorEnum.SUCCESS,
                bold=True,
            )
        )
        return data


class ConfirmOverwriteStep(PipelineStep):
    def execute(self, data):
        overwrite = data["overwrite"]

        if not overwrite.get("confirm") and not typer.confirm(overwrite.get("message")):
            error_message = (
                "Operation cancelled: The overwrite process was aborted by the user."
            )
            raise typer.Abort(error_message)
        return data


class DeletePageStep(PipelineStep):
    def execute(self, data):
        active_config = data["active_config"]
        page_key = data["page_key"]
        url, headers = build_endpoint(
            route=PAGE_API_ROUTES["detail"],
            page_key=page_key,
            active_config=active_config,
        )
        delete_page(url, headers, page_key)
        return data


class LoadTemplateZipStep(PipelineStep):
    def execute(self, data):
        template_path = Path(__file__).parent.parent / "templates" / "default-page.zip"

        if not template_path.exists():
            msg = f"Default page template not found at {template_path}"
            raise FileNotFoundError(msg)

        with open(template_path, "rb") as f:
            zip_content = f.read()

        data["zip_file"] = zip_content
        return data
