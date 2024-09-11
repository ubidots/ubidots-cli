import time
import zipfile
from dataclasses import dataclass
from dataclasses import field
from io import BytesIO
from pathlib import Path

import httpx
import typer

from cli.commons.pipelines import PipelineStep
from cli.commons.styles import print_colored_table
from cli.commons.utils import build_endpoint
from cli.commons.utils import check_response_status
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.manager import FunctionEngineClientManager
from cli.functions.engines.settings import engine_settings
from cli.functions.enums import FunctionHandlerFileExtensionEnum
from cli.functions.exceptions import FolderAlreadyExistsException
from cli.functions.exceptions import PermissionDeniedException
from cli.functions.exceptions import TemplateNotFoundException
from cli.functions.helpers import argo_container_manager
from cli.functions.helpers import compress_project_to_zip
from cli.functions.helpers import create_handler_file
from cli.functions.helpers import enumerate_project_files
from cli.functions.helpers import frie_container_manager
from cli.functions.helpers import get_argo_input_adapter
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

        project_metadata = data.get("project_metadata")
        kwargs = data.get("function_kwargs", {})
        language = data.get("language")
        runtime = data.get("runtime")

        if project_metadata and not language:
            language = project_metadata.project.language

        if project_metadata and not runtime:
            runtime = project_metadata.project.runtime

        if methods := project_metadata.function.methods:
            kwargs["methods"] = methods

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


class ShowStartupInfoStep(PipelineStep):
    def execute(self, data):
        project_metadata = data["project_metadata"]
        info_project = project_metadata.project
        function_kwargs = data["function_kwargs"]
        is_raw = function_kwargs["is_raw"]
        methods = project_metadata.function.methods or function_kwargs["methods"]
        token = function_kwargs["token"]

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
    Raw: {is_raw}
    Methods: {", ".join(methods)}
    Token: {token}
        """
        )
        return data


@dataclass
class ConfirmOverwriteStep(PipelineStep):
    confirm: bool
    message: str

    def execute(self, data):
        confirm = self.confirm
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
            f"{settings.FUNCTIONS.DEFAULT_HANDLER_FILE_NAME}.{FunctionHandlerFileExtensionEnum.PYTHON_EXTENSION}",
            f"{settings.FUNCTIONS.DEFAULT_HANDLER_FILE_NAME}.{FunctionHandlerFileExtensionEnum.NODEJS_EXTENSION}",
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
        data["response"] = response
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
        project_metadata = data["project_metadata"]
        hub_username = engine_settings.HUB_USERNAME
        function_image_name = f"{hub_username}/{project_metadata.project.runtime}"
        argo_image_name = f"{hub_username}/argo2:2.0.1"

        data["image_names"] = [
            argo_image_name,
            function_image_name,
        ]
        data["function_image_name"] = function_image_name
        data["argo_image_name"] = argo_image_name
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


class GetArgoContainerManagerStep(PipelineStep):
    def execute(self, data):
        client = data["client"]
        container_manager = data["container_manager"]
        network = data["network"]
        image_name = data["argo_image_name"]
        project_metadata = data["project_metadata"]

        container, argo_adapter_port = argo_container_manager(
            container_manager=container_manager,
            client=client,
            network=network,
            image_name=image_name,
            frie_label=project_metadata.project.label,
        )
        data["argo_container"] = container
        data["argo_adapter_port"] = argo_adapter_port
        return data


class GetArgoContainerIPAddressStep(PipelineStep):
    def execute(self, data):
        client = data["client"]
        container = data["argo_container"]
        network = data["network"]

        def get_ip_address(container):
            return container.attrs["NetworkSettings"]["Networks"][network.name][
                "IPAddress"
            ]

        ip_address = get_ip_address(container)
        if not ip_address:
            container = client.client.containers.get(container.name)
            ip_address = get_ip_address(container)
        data["ip_address"] = ip_address
        return data


class GetArgoContainerInputAdapterStep(PipelineStep):
    def execute(self, data):
        client = data["client"]
        network = data["network"]
        project_metadata = data["project_metadata"]
        argo_adapter_port = data["argo_adapter_port"]
        ip_address = data["ip_address"]
        function_kwargs = data["function_kwargs"]
        is_raw = function_kwargs["is_raw"]
        token = function_kwargs["token"]
        methods = project_metadata.function.methods or function_kwargs["methods"]

        adapter_url, adapter_data = get_argo_input_adapter(
            client=client,
            network=network,
            frie_label=project_metadata.project.label,
            argo_adapter_port=argo_adapter_port,
            is_raw=is_raw,
            ip_address=ip_address,
            token=token,
            methods=methods,
        )
        data["adapter_url"] = adapter_url
        data["adapter_data"] = adapter_data
        return data


class CreateArgoContainerAdapterStep(PipelineStep):
    def execute(self, data):
        adapter_url = data["adapter_url"]
        adapter_data = data["adapter_data"]

        time.sleep(settings.FUNCTIONS.CONTAINER_STARTUP_DELAY_SECONDS)
        http_client = httpx.Client(follow_redirects=True)
        http_client.post(adapter_url, json=adapter_data)
        return data


class CreateHandlerFRIEStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        project_metadata = data["project_metadata"]

        data["handler_path"] = create_handler_file(
            project_path, project_metadata.project.language
        )
        return data


class RemoveHandlerFRIEStep(PipelineStep):
    def execute(self, data):
        container_key = data["container_key"]
        container_manager = data["container_manager"]

        container = container_manager.get(
            f"{engine_settings.CONTAINER.FRIE.LABEL_KEY}={container_key}"
        )
        project_path = Path(container.attrs["Mounts"][0]["Source"])
        for pattern in [
            f"{settings.FUNCTIONS.DEFAULT_HANDLER_FILE_NAME}.{FunctionHandlerFileExtensionEnum.PYTHON_EXTENSION}",
            f"{settings.FUNCTIONS.DEFAULT_HANDLER_FILE_NAME}.{FunctionHandlerFileExtensionEnum.NODEJS_EXTENSION}",
        ]:
            for handler_file in project_path.glob(pattern):
                handler_file.unlink()
        return data


class GetFRIEContainerTargetStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        project_metadata = data["project_metadata"]
        container_manager = data["container_manager"]
        function_image_name = data["function_image_name"]
        network = data["network"]
        ip_address = data["ip_address"]
        function_kwargs = data["function_kwargs"]
        is_raw = function_kwargs["is_raw"]

        label = project_metadata.project.label
        argo_target_port = engine_settings.CONTAINER.ARGO.INTERNAL_TARGET_PORT.split(
            "/"
        )[0]
        target_url = f"http://{ip_address}:{argo_target_port}/{label}"
        frie_container_manager(
            container_manager=container_manager,
            project_path=project_path,
            network=network,
            image_name=function_image_name,
            label=label,
            is_raw=is_raw,
            target_url=target_url,
        )
        data["function_kwargs"]["label"] = label
        data["target_url"] = target_url
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
