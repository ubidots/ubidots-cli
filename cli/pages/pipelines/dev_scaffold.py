import zipfile
from pathlib import Path

import httpx

from cli.commons.pipelines import PipelineStep
from cli.commons.utils import build_endpoint
from cli.commons.utils import cleanup_directory
from cli.config.helpers import get_configuration
from cli.functions.exceptions import PermissionDeniedError
from cli.pages.exceptions import CurrentPlanDoesNotIncludePagesFeature
from cli.pages.exceptions import PageAlreadyExistsInCurrentDirectoryError
from cli.pages.exceptions import PageWithNameAlreadyExistsError
from cli.pages.exceptions import TemplateNotFoundError
from cli.pages.helpers import create_and_save_page_manifest
from cli.pages.helpers import read_page_manifest
from cli.pages.models import PageModelFactory
from cli.settings import settings


class ReadManifestStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        data["project_metadata"] = read_page_manifest(project_path)
        return data


class ValidateNotRunningFromPageDirectoryStep(PipelineStep):
    def execute(self, data):
        current_dir = Path.cwd()
        manifest_file = current_dir / settings.PAGES.PROJECT_MANIFEST_FILE
        if manifest_file.exists():
            raise PageAlreadyExistsInCurrentDirectoryError
        return data


class GetActiveConfigStep(PipelineStep):
    def execute(self, data):
        profile = data.get("profile", "")
        data["active_config"] = get_configuration(profile=profile)
        return data


class ValidatePagesAvailabilityPerPlanStep(PipelineStep):
    def execute(self, data):
        active_config = data["active_config"]

        url, headers = build_endpoint(
            route=settings.PAGES.API_ROUTES["base"],
            active_config=active_config,
        )

        try:
            response = httpx.get(url, headers=headers)
            response.raise_for_status()
            return data
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 402:
                raise CurrentPlanDoesNotIncludePagesFeature from e
            raise


class ValidateTemplateStep(PipelineStep):
    def execute(self, data):
        page_type = data["page_type"]
        template_file = settings.PAGES.UBIDOTS_PAGE_LAYOUT_ZIP[page_type.value]
        if not template_file.exists():
            raise TemplateNotFoundError(
                page_type=page_type,
                template_file=template_file,
            )
        data["template_file"] = template_file
        return data


class CreateProjectFolderStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        try:
            project_path.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            raise PageWithNameAlreadyExistsError(
                name=data["page_name"], page_path=project_path
            ) from None
        except PermissionError as error:
            raise PermissionDeniedError(error=str(error)) from error
        return data


class ExtractTemplateStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        template_file = data["template_file"]

        with zipfile.ZipFile(template_file, "r") as zip_ref:
            zip_ref.extractall(project_path)

        return data


class ValidateExtractedPageStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        page_type = data["page_type"]

        try:
            page_model = PageModelFactory.create_page_model_from_project(
                project_path, page_type
            )

            validation_result = page_model.validate_complete(project_path)

            if not validation_result["valid"]:
                if data.get("clean_directory_if_validation_fails", False):
                    cleanup_directory(project_path)

                errors = "; ".join(validation_result["errors"])
                msg = f"Page validation failed: {errors}"
                raise ValueError(msg)

            data["page_validation"] = validation_result
            return data

        except Exception as e:
            if data.get("clean_directory_if_validation_fails", False):
                cleanup_directory(project_path)

            msg = f"Page validation failed: {e!s}"
            raise ValueError(msg) from e


class SaveManifestStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        page_name = data["page_name"]
        page_type = data["page_type"]

        metadata = create_and_save_page_manifest(project_path, page_name, page_type)

        data["project_metadata"] = metadata
        return data
