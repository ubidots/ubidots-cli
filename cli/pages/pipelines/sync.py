import zipfile
from dataclasses import dataclass
from dataclasses import field
from io import BytesIO
from pathlib import Path

import httpx
import typer

from cli.commons.enums import MessageColorEnum
from cli.commons.pipelines import PipelineStep
from cli.commons.utils import build_endpoint
from cli.commons.utils import check_response_status
from cli.pages.constants import PAGE_API_ROUTES
from cli.pages.handlers import add_page
from cli.pages.handlers import download_page_code
from cli.pages.handlers import upload_page_code
from cli.pages.helpers import compress_page_to_zip
from cli.pages.helpers import create_and_save_page_manifest
from cli.pages.helpers import read_page_manifest
from cli.pages.helpers import save_page_manifest
from cli.pages.models import PageTypeEnum
from cli.settings import settings


class ValidateRemotePageExistStep(PipelineStep):
    def execute(self, data):
        data["needs_update"] = False

        project_metadata = data["project_metadata"]
        remote_id = project_metadata.page.id
        if not remote_id:
            return data

        url, headers = build_endpoint(
            route=PAGE_API_ROUTES["detail"],
            page_key=remote_id,
            active_config=data["active_config"],
        )
        try:
            response = httpx.get(url=url, headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            if error.response.status_code == httpx.codes.NOT_FOUND:
                return data
            raise error
        data["needs_update"] = True
        data["remote_id"] = remote_id
        return data


class CreatePageIfNeededStep(PipelineStep):
    def execute(self, data):
        if data["needs_update"]:
            return data

        message = (
            "This page is not created. Would you like to create a new page and push it?"
        )
        if not typer.confirm(message):
            error_message = "Operation cancelled: Page pushing was aborted by the user."
            raise typer.Abort(error_message)

        active_config = data["active_config"]
        project_metadata = data["project_metadata"]
        name = project_metadata.project.name
        label = project_metadata.project.label

        response = add_page(
            active_config=active_config,
            name=name,
            label=label,
        )

        if response.status_code not in (httpx.codes.OK, httpx.codes.CREATED):
            msg = f"Failed to create page: {response.text}"
            raise RuntimeError(msg)

        response_data = response.json()
        data["remote_id"] = response_data.get("id", "")
        data["page_label"] = response_data.get("label", label)
        return data


class SavePageRemoteIdStep(PipelineStep):
    def execute(self, data):
        if data["needs_update"]:
            return data

        project_metadata = data["project_metadata"]
        project_path = data["project_path"]
        remote_id = data["remote_id"]

        project_metadata.page.id = remote_id

        save_page_manifest(project_path, project_metadata)

        return data


class ConfirmOverwritePushPageStep(PipelineStep):
    def execute(self, data):
        needs_update = data["needs_update"]
        confirm = data.get("confirm", False)

        if not needs_update:
            return data

        message = "This page has already been pushed. Would you like to overwrite the remote page?"
        if not confirm and not typer.confirm(message):
            error_message = (
                "Operation cancelled: The pushing process was aborted by the user."
            )
            raise typer.Abort(error_message)
        return data


@dataclass
class CompressPageProjectStep(PipelineStep):
    exclude_files: list[str] = field(
        default_factory=lambda: [
            settings.PAGES.PROJECT_METADATA_FILE,
        ]
    )

    def execute(self, data):
        project_path = data["project_path"]

        zip_file = compress_page_to_zip(
            project_path=project_path,
            exclude_files=self.exclude_files,
        )
        data["zip_file"] = zip_file
        return data


class UploadPageCodeStep(PipelineStep):
    def execute(self, data):
        url = data["url"]
        headers = data["headers"]
        zip_file = data["zip_file"]

        page_name = (
            data["project_metadata"].project.name
            if "project_metadata" in data
            else data.get("page_name", "page")
        )

        response = upload_page_code(
            url=url,
            headers=headers,
            zip_file=zip_file,
            page_name=page_name,
        )
        data["response"] = response
        return data


class CheckRemotePageIdRequirementStep(PipelineStep):
    def execute(self, data):
        remote_id = data.get("remote_id", "")
        project_path = data["project_path"]

        metadata_file = project_path / settings.PAGES.PROJECT_METADATA_FILE

        if not metadata_file.exists():
            if not remote_id:
                error_message = "Error: '--remote-id <page-id>' is required when not in a page directory."
                raise ValueError(error_message)
            data["is_new_page_pull"] = True
        else:
            try:
                project_metadata = read_page_manifest(project_path)
                page_id = getattr(project_metadata.page, "id", None)

                if page_id:
                    data["remote_id"] = page_id
                    data["is_existing_page_pull"] = True

                    if remote_id and remote_id != page_id:
                        warning_message = (
                            f"\n> [WARNING]: Ignoring provided remote ID '{remote_id}'. "
                            f"Using page ID from local metadata '{page_id}' instead.\n"
                        )
                        typer.echo(
                            typer.style(
                                text=warning_message,
                                fg=MessageColorEnum.WARNING,
                                bold=True,
                            )
                        )
                else:
                    if not remote_id:
                        error_message = "Page metadata is missing an ID."
                        raise ValueError(error_message)
            except Exception as e:
                if not remote_id:
                    error_message = "The page has not been registered or synchronized with the platform."
                    raise ValueError(error_message) from e
        return data


class GetRemotePageDetailStep(PipelineStep):
    def execute(self, data):
        url, headers = build_endpoint(
            route=PAGE_API_ROUTES["detail"],
            page_key=data["remote_id"],
            active_config=data["active_config"],
        )
        response = httpx.get(url, headers=headers, follow_redirects=True)
        data["remote_page_detail_response"] = response
        return data


class CheckPageDetailResponseStep(PipelineStep):
    def execute(self, data):
        response = data["remote_page_detail_response"]
        remote_id = data["remote_id"]
        error_message = f"Page with id '{remote_id}' not found."
        check_response_status(response=response, custom_message=error_message)
        return data


class ParsePageDetailsResponseStep(PipelineStep):
    def execute(self, data):
        response = data["remote_page_detail_response"].json()
        data["remote_page_detail"] = {
            "id": response.get("id"),
            "label": response.get("label"),
            "name": response.get("name"),
            "url": response.get("url", ""),
            "isActive": response.get("isActive", False),
            "createdAt": response.get("createdAt", ""),
        }
        return data


class GetRemotePageLocalMetadataStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        remote_page_name = data["remote_page_detail"]["name"]
        page_path = Path(project_path / remote_page_name)
        page_metadata_file = Path(
            project_path / remote_page_name / settings.PAGES.PROJECT_METADATA_FILE
        )
        if page_metadata_file.exists():
            data["existing_project_metadata"] = read_page_manifest(page_path)
        return data


class ValidatePageHasAlreadyBeenPulledStep(PipelineStep):
    def execute(self, data):
        data["needs_update"] = False
        if not data.get("existing_project_metadata"):
            return data

        remote_page_id = data["remote_id"]
        remote_page_name = data["remote_page_detail"]["name"]
        existing_page_name = data["existing_project_metadata"].project.name
        project_path = data["project_path"]
        page_path = Path(project_path / remote_page_name)
        if not page_path.exists():
            return data
        existing_metadata_page_id = data["existing_project_metadata"].page.id
        if existing_metadata_page_id == remote_page_id:
            data["needs_update"] = True
        if remote_page_name == existing_page_name:
            data["needs_update"] = True
        return data


class ConfirmOverwritePullPageStep(PipelineStep):
    def execute(self, data):
        needs_update = data["needs_update"]
        confirm = data.get("confirm", False)

        if not needs_update:
            return data
        message = "This page has already been pulled. Would you like to overwrite it?"
        if not confirm and not typer.confirm(message):
            error_message = (
                "Operation cancelled: The overwrite process was aborted by the user."
            )
            raise typer.Abort(error_message)
        return data


class DownloadPageCodeStep(PipelineStep):
    def execute(self, data):
        url, headers = build_endpoint(
            route=PAGE_API_ROUTES["code"],
            page_key=data["remote_id"],
            active_config=data["active_config"],
        )
        response = download_page_code(url, headers)

        if response.status_code == 400:
            try:
                error_detail = response.json().get("detail", "")
                if "requested file could not be found" in error_detail.lower():
                    data["has_code"] = False
                    data["page_zip_content"] = None
                    return data
            except Exception:
                pass

        data["has_code"] = True
        data["page_zip_content"] = response
        return data


@dataclass
class CheckPageResponseStep(PipelineStep):
    response_key: str

    def execute(self, data):
        if not data.get("has_code", True):
            return data

        response = data[self.response_key]
        check_response_status(response)
        return data


class ExtractPageProjectStep(PipelineStep):
    def execute(self, data):
        if not data.get("has_code", True):
            return data

        project_path = data["project_path"]
        response = data["page_zip_content"]
        remote_page_name = data["remote_page_detail"]["name"]

        metadata_file = project_path / settings.PAGES.PROJECT_METADATA_FILE
        in_page_dir = metadata_file.exists()

        extract_path = (
            project_path if in_page_dir else Path(project_path / remote_page_name)
        )

        with zipfile.ZipFile(BytesIO(response.content), "r") as zip_ref:
            zip_ref.extractall(extract_path)

        if not in_page_dir:
            data["project_path"] = extract_path

        return data


class SavePullPageManifestStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        remote_page_detail = data["remote_page_detail"]
        page_name = remote_page_detail["name"]
        page_id = remote_page_detail["id"]
        has_code = data.get("has_code", True)

        if not has_code and data.get("is_new_page_pull", False):
            page_dir = project_path / page_name
            page_dir.mkdir(parents=True, exist_ok=True)
            data["project_path"] = page_dir
            project_path = page_dir

        create_and_save_page_manifest(
            project_path=project_path,
            page_name=page_name,
            page_type=PageTypeEnum.DASHBOARD,
            page_id=page_id,
        )

        return data


class PrintPagePathStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        has_code = data.get("has_code", True)
        page_name = data["remote_page_detail"]["name"]

        if data.get("is_new_page_pull", False):
            remote_id = data.get("remote_id", "")
            success_msg = f"\n> [DONE]: Page '{page_name}' (id: {remote_id}) was pulled successfully to {project_path}"
            if not has_code:
                success_msg += "\n> [NOTE]: This page has no code uploaded yet. Use 'pages push' to upload code."
            success_msg += "\n"
            typer.echo(
                typer.style(
                    text=success_msg,
                    fg=MessageColorEnum.SUCCESS,
                    bold=True,
                )
            )
        elif data.get("is_existing_page_pull", False):
            typer.echo(
                typer.style(
                    text="\n> [DONE]: Page was pulled successfully\n",
                    fg=MessageColorEnum.SUCCESS,
                    bold=True,
                )
            )
        return data
