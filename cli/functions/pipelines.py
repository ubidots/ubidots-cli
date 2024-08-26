import zipfile
from dataclasses import dataclass
from dataclasses import field
from io import BytesIO

import httpx
import typer

from cli.commons.pipelines import PipelineStep
from cli.commons.styles import print_colored_table
from cli.commons.utils import build_endpoint
from cli.commons.utils import check_response_status
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.manager import FunctionEngineClientManager
from cli.functions.engines.settings import engine_settings
from cli.functions.enums import FunctionMethodEnum
from cli.functions.exceptions import FolderAlreadyExistsException
from cli.functions.exceptions import PermissionDeniedException
from cli.functions.exceptions import TemplateNotFoundException
from cli.functions.helpers import compress_project_to_zip
from cli.functions.helpers import enumerate_project_files
from cli.functions.helpers import get_or_create_network
from cli.functions.helpers import read_manifest_project_file
from cli.functions.helpers import save_manifest_project_file
from cli.functions.helpers import verify_and_fetch_images
from cli.functions.validators import validate_main_file_presence
from cli.functions.validators import validate_manifest_file
from cli.settings import settings


class ValidateTemplateStep(PipelineStep):
    def execute(self, data):
        language = data["language"]
        template_file = data["template_file"]
        if not template_file.exists():
            raise TemplateNotFoundException(
                language=language,
                template_file=template_file,
            )
        return data


class CreateProjectFolderStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        if project_path.exists():
            raise FolderAlreadyExistsException(name=project_path.name)
        try:
            project_path.mkdir(parents=True, exist_ok=False)
        except PermissionError as error:
            raise PermissionDeniedException(error=str(error)) from error
        return data


class ExtractTemplateStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        template_file = data["template_file"]
        with zipfile.ZipFile(template_file, "r") as zip_ref:
            zip_ref.extractall(project_path)
        return data


class SaveManifestStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        language = data["language"]
        runtime = data["runtime"]
        kwargs = data.get("kwargs", {})
        save_manifest_project_file(
            project_path=project_path,
            language=language,
            runtime=runtime,
            **kwargs,
        )
        return data


class ReadManifestStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        data["project_metadata"] = read_manifest_project_file(project_path)
        return data


class GetProjectFilesStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        data["project_files"] = enumerate_project_files(project_path)
        return data


@dataclass
class ValidateProjectStep(PipelineStep):
    validate_manifest_file: bool = True
    validate_main_file_presence: bool = True

    def execute(self, data):
        project_path = data["project_path"]
        project_files = data["project_files"]
        project_metadata = data["project_metadata"]
        if self.validate_manifest_file:
            validate_manifest_file(project_metadata.function.id)
        if self.validate_main_file_presence:
            validate_main_file_presence(
                project_path=project_path,
                project_files=project_files,
                main_file=project_metadata.project.language.main_file,
            )
        return data


@dataclass
class ShowStartupInfoStep(PipelineStep):
    is_raw: bool
    method: FunctionMethodEnum
    token: str

    def execute(self, data):
        project_metadata = data["project_metadata"]
        info_project = project_metadata.project
        typer.echo(
            f"""
    ------------------
    Starting Function:
    ------------------
    Name: {info_project.name}
    Runtime: {info_project.runtime}
    Local label: {info_project.label}

    -------
    INPUTS:
    -------
    Raw: {self.is_raw}
    Method: {self.method}
    Token: {self.token}
        """
        )
        return data


@dataclass
class ConfirmOverwriteStep(PipelineStep):
    confirm: bool
    message: str

    def execute(self, data):
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
        default_factory=lambda: [
            settings.FUNCTIONS.PROJECT_METADATA_FILE,
            settings.FUNCTIONS.DEFAULT_HANLDER_FILE_NAME,
        ]
    )

    def execute(self, data):
        project_path = data["project_path"]
        zip_file = compress_project_to_zip(
            project_path=project_path,
            exclude_files=self.exclude_files,
        )
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
        check_response_status(response)
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
    engine: FunctionEngineTypeEnum = engine_settings.CONTAINER.DEFAULT_ENGINE

    def execute(self, data):
        engine_manager = FunctionEngineClientManager(self.engine)
        data["client"] = engine_manager.get_client()
        return data


class GetContainerManagerStep(PipelineStep):
    def execute(self, data):
        client = data["client"]
        data["container_manager"] = client.get_container_manager()
        return data


class GetImageNamesStep(PipelineStep):
    def execute(self, data):
        # project_metadata = data["project_metadata"]
        hub_username = engine_settings.HUB_USERNAME
        data["image_names"] = [
            # f"{hub_username}/{project_metadata.project.runtime.value}",
            f"{hub_username}/python3.9-base:latest",
            f"{hub_username}/argo2:2.0.1",
        ]
        return data


class ValidateImageNamesStep(PipelineStep):
    def execute(self, data):
        client = data["client"]
        image_names = data["image_names"]
        verify_and_fetch_images(client=client, image_names=image_names)
        return data


class GetClientNetworkStep(PipelineStep):
    def execute(self, data):
        client = data["client"]
        data["network"] = get_or_create_network(client)
        return data


@dataclass
class GetFunctionLogsStep(PipelineStep):
    tail: int | str
    follow: bool

    def execute(self, data):
        container_key = data["container_key"]
        container_manager = data["container_manager"]
        data["logs"] = container_manager.logs(
            label=f"{engine_settings.CONTAINER.FRIE.LABEL_KEY}={container_key}",
            tail=self.tail,
            follow=self.follow,
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
