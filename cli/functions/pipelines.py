import zipfile
from dataclasses import dataclass
from dataclasses import field
from io import BytesIO
from typing import Any

import httpx
import typer

from cli.commons.styles import print_colored_table
from cli.commons.utils import build_endpoint
from cli.commons.utils import check_response_status
from cli.commons.utils import exit_with_error_message
from cli.commons.utils import exit_with_success_message
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.manager import FunctionEngineClientManager
from cli.functions.engines.settings import engine_settings
from cli.functions.enums import FunctionProjectValidationTypeEnum
from cli.functions.exceptions import FolderAlreadyExistsException
from cli.functions.exceptions import PermissionDeniedException
from cli.functions.exceptions import TemplateNotFoundException
from cli.functions.helpers import compress_project_to_zip
from cli.functions.helpers import ensure_project_integrity
from cli.functions.helpers import save_manifest_project_file
from cli.settings import settings


@dataclass
class Pipeline:
    steps: list["PipelineStep"]
    success_message: str = ""

    def _handle_success(self) -> None:
        if self.success_message:
            exit_with_success_message(self.success_message)

    def _handle_failure(self, step: "PipelineStep", exception: Exception) -> None:
        _ = step
        exit_with_error_message(exception=exception)

    def run(self, initial_data: dict[str, Any]) -> dict[str, Any]:
        data = initial_data
        for step in self.steps:
            try:
                data = step.execute(data)
            except Exception as error:
                self._handle_failure(step, error)
                break

        else:
            self._handle_success()
        return data


class PipelineStep:
    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        _ = data
        error_message = "Each step must implement the execute method."
        raise NotImplementedError(error_message)


class ValidateTemplateStep(PipelineStep):
    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        language = data["language"]
        template_file = settings.FUNCTIONS.TEMPLATES_PATH / f"{language}.zip"
        if not template_file.exists():
            raise TemplateNotFoundException(
                language=language, template_file=template_file
            )
        data["template_file"] = template_file
        return data


class CreateProjectFolderStep(PipelineStep):
    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        project_path = data["project_path"]
        if project_path.exists():
            raise FolderAlreadyExistsException(name=project_path.name)
        try:
            project_path.mkdir(parents=True, exist_ok=False)
        except PermissionError as error:
            raise PermissionDeniedException(error=error) from error
        return data


class ExtractTemplateStep(PipelineStep):
    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        project_path = data["project_path"]
        template_file = data["template_file"]
        with zipfile.ZipFile(template_file, "r") as zip_ref:
            zip_ref.extractall(project_path)
        return data


class SaveManifestStep(PipelineStep):
    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        project_path = data["project_path"]
        language = data["language"]
        runtime = data["runtime"]
        save_manifest_project_file(
            project_path=project_path,
            engine=FunctionEngineTypeEnum.DOCKER,
            label="",
            language=language,
            runtime=runtime,
        )
        return data


class ValidateProjectStep(PipelineStep):
    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        project_path = data["project_path"]
        project_metadata = ensure_project_integrity(
            project_path=project_path,
            validation_flags={
                FunctionProjectValidationTypeEnum.MANIFEST_FILE: True,
                FunctionProjectValidationTypeEnum.MAIN_FILE_PRESENCE: True,
            },
        )
        data["project_metadata"] = project_metadata
        return data


@dataclass
class ConfirmOverwriteStep(PipelineStep):
    confirm: bool
    message: str

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        project_metadata = data["project_metadata"]
        confirm = self.confirm or project_metadata.globals.auto_overwrite
        if not confirm and not typer.confirm(self.message):
            error_message = (
                "Operation cancelled: The overwrite process was aborted by the user."
            )
            raise typer.Abort(error_message)
        return data


@dataclass
class CompressProjectStep(PipelineStep):
    exclude_files: list[str] = field(
        default_factory=lambda: [settings.FUNCTIONS.PROJECT_METADATA_FILE]
    )

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        project_path = data["project_path"]
        zip_file = compress_project_to_zip(project_path, self.exclude_files)
        data["zip_file"] = zip_file
        return data


class ExtractProjectStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        response = data["response"]
        with zipfile.ZipFile(BytesIO(response.content), "r") as zip_ref:
            zip_ref.extractall(project_path)
        return data


@dataclass
class BuildEndpointStep(PipelineStep):
    api_route: str

    def execute(self, data):
        project_metadata = data["project_metadata"]
        url, headers = build_endpoint(
            route=self.api_route,
            function_key=project_metadata.function.id,
        )
        data["url"] = url
        data["headers"] = headers
        return data


class UploadFileStep(PipelineStep):
    def execute(self, data):
        url = data["url"]
        headers = data["headers"]
        zip_file = data["zip_file"]
        project_metadata = data["project_metadata"]
        files = {
            "zipFile": (
                f"{project_metadata.project.name}.zip",
                zip_file,
                "application/zip",
            )
        }
        client = httpx.Client(follow_redirects=True)
        response = client.post(url=url, headers=headers, files=files)
        data["response"] = response
        return data


class HttpGetRequestStep(PipelineStep):
    def execute(self, data):
        url = data["url"]
        headers = data["headers"]
        response = httpx.get(url, headers=headers)
        data["results"] = response.json()["results"]
        return data


class DownloadFileStep(PipelineStep):
    def execute(self, data):
        url = data["url"]
        headers = data["headers"]
        response = httpx.get(url, headers=headers)
        data["response"] = response
        return data


class CheckResponseStep(PipelineStep):
    def execute(self, data):
        response = data["response"]
        check_response_status(response=response)
        return data


@dataclass
class PrintColoredTableStep(PipelineStep):
    key: str = ""

    def execute(self, data):
        if self.key and self.key in data:
            results = data[self.key]
            print_colored_table(results)
        return data


@dataclass
class PrintkeyStep(PipelineStep):
    key: str = ""

    def execute(self, data):
        if self.key and self.key in data:
            text = data[self.key]
            typer.echo(text)
        return data


@dataclass
class GetClientStep(PipelineStep):
    engine: FunctionEngineTypeEnum

    def execute(self, data):
        engine_manager = FunctionEngineClientManager(engine=self.engine)
        data["client"] = engine_manager.get_client()
        return data


class GetContainerManagerStep(PipelineStep):
    def execute(self, data):
        client = data["client"]
        data["container_manager"] = client.get_container_manager()
        return data


@dataclass
class GetFunctionLogsStep(PipelineStep):
    tail: int | str = "all"
    follow: bool = False

    def execute(self, data):
        container_key = data["container_key"]
        container_manager = data["container_manager"]
        data["logs"] = container_manager.logs(
            key=container_key, tail=self.tail, follow=self.follow
        )
        return data


class GetFunctionStatusStep(PipelineStep):
    def execute(self, data):
        container_manager = data["container_manager"]
        data["status"] = container_manager.status(
            container_label_key=engine_settings.CONTAINER.FRIE.LABEL_KEY,
            is_raw_label_key=engine_settings.CONTAINER.FRIE.IS_RAW_LABEL_KEY,
            target_url_label_key=engine_settings.CONTAINER.FRIE.URL_LABEL_KEY,
        )
        return data


class StopFunctionStep(PipelineStep):
    def execute(self, data):
        container_key = data["container_key"]
        container_manager = data["container_manager"]
        container_manager.stop(
            f"{engine_settings.CONTAINER.FRIE.LABEL_KEY}={container_key}"
        )
        return data
