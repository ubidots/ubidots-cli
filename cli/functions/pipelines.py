import json
import shutil
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
from cli.config.helpers import get_active_profile_configuration
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.manager import FunctionEngineClientManager
from cli.functions.engines.settings import engine_settings
from cli.functions.enums import FunctionHandlerFileExtensionEnum
from cli.functions.enums import FunctionMainFileExtensionEnum
from cli.functions.enums import FunctionMethodEnum
from cli.functions.exceptions import FolderAlreadyExistsError
from cli.functions.exceptions import FunctionWithIdAlreadyExistsError
from cli.functions.exceptions import FunctionWithNameAlreadyExistsError
from cli.functions.exceptions import PermissionDeniedError
from cli.functions.exceptions import TemplateNotFoundError
from cli.functions.helpers import argo_container_manager
from cli.functions.helpers import build_functions_payload
from cli.functions.helpers import compress_project_to_zip
from cli.functions.helpers import create_handler_file
from cli.functions.helpers import enumerate_project_files
from cli.functions.helpers import frie_container_manager
from cli.functions.helpers import get_argo_input_adapter
from cli.functions.helpers import get_language_from_runtime
from cli.functions.helpers import get_or_create_network
from cli.functions.helpers import read_manifest_project_file
from cli.functions.helpers import save_manifest_project_file
from cli.functions.helpers import verify_and_fetch_images
from cli.functions.validators import validate_function_exists
from cli.functions.validators import validate_main_file_exists
from cli.settings import settings


class ValidateTemplateStep(PipelineStep):
    def execute(self, data):
        language = data["language"]
        template_file = data["template_file"]

        if not template_file.exists():
            raise TemplateNotFoundError(
                language=language,
                template_file=template_file,
            )
        return data


class CreateProjectFolderStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]

        if project_path.exists():
            raise FolderAlreadyExistsError(name=project_path.name)
        try:
            project_path.mkdir(parents=True, exist_ok=False)
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


class SaveManifestStep(PipelineStep):
    def execute(self, data):
        save_manifest_project_file(**data)
        return data


class ValidateRuntimeAgaisntLanguageStep(PipelineStep):
    def execute(self, data):
        language = data["language"]
        runtime = data["runtime"]
        if not runtime.startswith(language):
            error_message = f"Runtime '{runtime}' does not match language '{language}'"
            raise ValueError(error_message)
        return data


class ValidateAllowedRuntimeStep(PipelineStep):
    def execute(self, data):
        runtime = data["runtime"]
        profile_config = get_active_profile_configuration()
        allowed_runtimes = profile_config.runtimes
        if runtime not in allowed_runtimes:
            error_message = f"Runtime '{runtime}' is not allowed"
            raise ValueError(error_message)
        return data


class GetTokenFromProfileStep(PipelineStep):
    def execute(self, data):
        profile_config = get_active_profile_configuration()
        data["token"] = profile_config.access_token
        return data


class SetTokenInManifestStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        data["project_metadata"] = read_manifest_project_file(project_path)
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


class GetProjectMetadataStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        remote_function_name = data["remote_function_detail"]["name"]
        function_path = Path(project_path / remote_function_name)
        function_yaml_file = Path(
            project_path
            / remote_function_name
            / settings.FUNCTIONS.PROJECT_METADATA_FILE
        )
        if function_yaml_file.exists():
            data["existing_project_metadata"] = read_manifest_project_file(
                function_path
            )
        return data


class GetFunctionParametersStep(PipelineStep):
    def execute(self, data):
        remote_function_details = data["remote_function_detail"]
        data["name"] = (name := remote_function_details["name"])
        data["language"] = get_language_from_runtime(
            runtime := remote_function_details["serverless"]["runtime"]
        )
        data["runtime"] = runtime
        data["methods"] = remote_function_details["triggers"]["httpMethods"]
        data["label"] = remote_function_details["label"]
        data["created_at"] = remote_function_details["createdAt"]
        data["timeout"] = remote_function_details["serverless"]["timeout"]
        data["http_is_secure"] = remote_function_details["serverless"]["httpIsSecure"]
        data["http_enabled"] = remote_function_details["serverless"]["httpEnabled"]
        data["engine"] = settings.CONFIG.DEFAULT_CONTAINER_ENGINE
        data["has_cors"] = remote_function_details["serverless"]["httpHasCors"]
        data["is_raw"] = remote_function_details["serverless"]["isRawFunction"]
        data["cron"] = remote_function_details["serverless"]["schedulerCron"]
        data["has_cron"] = remote_function_details["serverless"]["schedulerEnabled"]
        data["function_id"] = remote_function_details["id"]
        data["token"] = remote_function_details["serverless"]["authToken"]
        data["params"] = remote_function_details["serverless"]["params"]
        data["project_path"] = data["project_path"] / name
        return data


class ValidateFunctionAlreadyExistsStep(PipelineStep):
    def execute(self, data):
        if not data.get("existing_project_metadata"):
            return data
        remote_function_id = data["remote_id"]
        remote_function_name = data["remote_function_detail"]["name"]
        existing_function_name = data["existing_project_metadata"].project.name
        project_path = data["project_path"]
        function_path = Path(project_path / remote_function_name)
        if not function_path.exists():
            return data
        existing_metadata_function_id = data["existing_project_metadata"].function.id
        if existing_metadata_function_id == remote_function_id:
            raise FunctionWithIdAlreadyExistsError(
                id=remote_function_id,
                function_path=function_path,
                alternative_command="ubidots functions update",
            )
        if remote_function_name == existing_function_name:
            raise FunctionWithNameAlreadyExistsError(
                name=remote_function_name,
                function_path=function_path,
            )
        return data


class ValidateProjectStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        project_files = data["project_files"]
        project_metadata = data["project_metadata"]
        validations = data.get("validations", {})
        if validations.get("manifest_file"):
            validate_main_file_exists(
                project_path=project_path,
                project_files=project_files,
                main_file=project_metadata.project.language.main_file,
            )
        if validations.get("function_exists"):
            validate_function_exists(project_metadata.function.id)
        return data


class ShowStartupInfoStep(PipelineStep):
    def execute(self, data):
        project_metadata = data["project_metadata"]
        info_project = project_metadata.project
        is_raw = data.get("is_raw")
        if project_metadata and is_raw is None:
            is_raw = project_metadata.function.is_raw
        is_raw = False if is_raw is None else is_raw
        methods = (
            project_metadata.function.methods
            if not data.get("methods") and project_metadata
            else data.get("methods")
        )
        token = data.get("token") or project_metadata.function.token

        typer.echo(
            f"""
------------------
Starting Function:
------------------
Name: {info_project.name}
Runtime: {info_project.runtime}
Local label: {info_project.local_label}

-------
INPUTS:
-------
Raw: {is_raw}
Methods: {", ".join(methods)}
Token: {token}
    """
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


@dataclass
class CompressProjectStep(PipelineStep):
    exclude_files: list[str] = field(
        default_factory=lambda: [
            settings.FUNCTIONS.PROJECT_METADATA_FILE,
            f".{settings.FUNCTIONS.DEFAULT_MAIN_FUNCTION_NAME}.{FunctionMainFileExtensionEnum.PYTHON_EXTENSION}",
            f".{settings.FUNCTIONS.DEFAULT_MAIN_FUNCTION_NAME}.{FunctionMainFileExtensionEnum.NODEJS_EXTENSION}",
            f"{settings.FUNCTIONS.DEFAULT_HANDLER_FILE_NAME}.{FunctionHandlerFileExtensionEnum.PYTHON_EXTENSION}",
            f"{settings.FUNCTIONS.DEFAULT_HANDLER_FILE_NAME}.{FunctionHandlerFileExtensionEnum.NODEJS_EXTENSION}",
            "node_modules",
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
        response = data["function_zip_content"]
        remote_function_name = data["remote_function_detail"]["name"]
        function_path = Path(project_path / remote_function_name)

        with zipfile.ZipFile(BytesIO(response.content), "r") as zip_ref:
            zip_ref.extractall(function_path)
        return data


@dataclass
class BuildEndpointStep(PipelineStep):
    api_route: str

    def execute(self, data):
        function_key = data["remote_id"]
        active_config = get_active_profile_configuration()
        url, headers = build_endpoint(
            route=self.api_route, function_key=function_key, active_config=active_config
        )
        data["url"] = url
        data["headers"] = headers
        return data


class CreateFunctionStep(PipelineStep):
    def execute(self, data):
        url = data["url"]
        headers = data["headers"]
        project_metadata = data["project_metadata"]
        data["needs_update"] = False

        if project_metadata.function.id:
            data["needs_update"] = True
            return data

        message = "This function is not created. Would you like to create a new function and push it?"
        if not typer.confirm(message):
            error_message = (
                "Operation cancelled: The overwrite process was aborted by the user."
            )
            raise typer.Abort(error_message)

        json = build_functions_payload(
            label=project_metadata.function.label or "",
            name=project_metadata.project.name,
            triggers={
                "httpMethods": FunctionMethodEnum.enum_list_to_str_list(
                    project_metadata.function.methods
                ),
                "httpHasCors": project_metadata.function.has_cors,
                "schedulerCron": project_metadata.function.cron or None,
            },
            serverless={
                "runtime": project_metadata.project.runtime,
                "isRawFunction": project_metadata.function.is_raw,
                "authToken": None,
                "timeout": project_metadata.function.timeout,
                "params": project_metadata.function.payload,
            },
        )

        client = httpx.Client(follow_redirects=True)
        response = client.post(url, headers=headers, json=json)

        if response.status_code != httpx.codes.CREATED:
            raise (
                httpx.HTTPStatusError(
                    message=response._content.decode("utf-8"),
                    request=response.request,
                    response=response,
                )
            )
        data["response"] = response
        data["function_id"] = response.json()["id"]
        data["function_label"] = response.json()["label"]
        return data


class UpdateFunctionStep(PipelineStep):
    def execute(self, data):
        url = data["url"]
        headers = data["headers"]
        project_metadata = data["project_metadata"]

        if not project_metadata.function.id and not data.get("needs_update"):
            return data

        json = build_functions_payload(
            label=project_metadata.function.label or "",
            name=project_metadata.project.name,
            triggers={
                "httpMethods": FunctionMethodEnum.enum_list_to_str_list(
                    project_metadata.function.methods
                ),
                "httpHasCors": project_metadata.function.has_cors,
                "schedulerCron": project_metadata.function.cron or None,
            },
            serverless={
                "runtime": project_metadata.project.runtime,
                "isRawFunction": project_metadata.function.is_raw,
                "authToken": None,
                "timeout": project_metadata.function.timeout,
                "params": project_metadata.function.payload,
            },
        )

        response = httpx.patch(url, headers=headers, json=json)
        if response.status_code != httpx.codes.OK:
            raise (
                httpx.HTTPStatusError(
                    message=response._content.decode("utf-8"),
                    request=response.request,
                    response=response,
                )
            )
        data["response"] = response
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
        data["function_zip_content"] = response
        return data


@dataclass
class CheckResponseStep(PipelineStep):
    response_key: str

    def execute(self, data):
        response = data[self.response_key]
        check_response_status(response)
        return data


class CheckFunctionDetailResponse(PipelineStep):
    def execute(self, data):
        response = data["remote_function_detail"]
        remote_id = data["remote_id"]
        error_message = f"Function with id '{remote_id}' not found."
        check_response_status(response=response, custom_message=error_message)
        return data


class ParseFunctionDetailsResponse(PipelineStep):
    def execute(self, data):
        response = data["remote_function_detail"].json()
        serverless_resp = response.get("serverless", {})
        triggers_resp = response.get("triggers", {})
        params = serverless_resp.get("params")

        if isinstance(params, str):
            try:
                params = json.loads(params)
            except Exception:
                params = {}

        serverless_data = {
            "runtime": serverless_resp.get("runtime"),
            "params": params,
            "authToken": serverless_resp.get("authToken") or "",
            "isRawFunction": serverless_resp.get("isRawFunction"),
            "timeout": serverless_resp.get("timeout"),
            "httpHasCors": triggers_resp.get("httpHasCors"),
            "httpIsSecure": not triggers_resp.get("httpIsInsecure", False),
            "httpEnabled": triggers_resp.get("httpEnabled"),
            "schedulerCron": triggers_resp.get("schedulerCron") or "",
            "schedulerEnabled": triggers_resp.get("schedulerEnabled"),
        }
        triggers_data = {"httpMethods": triggers_resp.get("httpMethods")}
        function_model_data = {
            "id": response.get("id"),
            "label": response.get("label"),
            "serverless": serverless_data,
            "triggers": triggers_data,
        }
        data["remote_function_detail"] = function_model_data
        data["remote_function_detail"]["label"] = response.get("label")
        data["remote_function_detail"]["name"] = response.get("name")
        data["remote_function_detail"]["createdAt"] = response.get("createdAt")

        return data


@dataclass
class GetFunctionDetailSteps(PipelineStep):
    api_route: str

    def execute(self, data):
        active_config = get_active_profile_configuration()
        url, headers = build_endpoint(
            route=self.api_route,
            function_key=data["remote_id"],
            active_config=active_config,
        )
        response = httpx.get(url, headers=headers)
        data["remote_function_detail"] = response
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
        function_image_name = (
            f"{hub_username}/"
            f"{engine_settings.HUB_PREFFIX}-{project_metadata.project.runtime}"
        )
        argo_image_name = (
            f"{hub_username}/"
            f"{engine_settings.HUB_PREFFIX}-{engine_settings.CONTAINER.ARGO.NAME}:2.0.1"
        )

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
            frie_label=project_metadata.project.local_label,
        )
        data["argo_container"] = container
        data["argo_adapter_port"] = argo_adapter_port
        return data


class GetArgoContainerInputAdapterStep(PipelineStep):
    def execute(self, data):
        client = data["client"]
        network = data["network"]
        project_metadata = data["project_metadata"]
        argo_adapter_port = data["argo_adapter_port"]

        is_raw = data.get("is_raw")
        if project_metadata and is_raw is None:
            is_raw = project_metadata.function.is_raw
        is_raw = False if is_raw is None else is_raw
        has_cors = data.get("has_cors")
        if project_metadata and has_cors is None:
            has_cors = project_metadata.function.has_cors
        has_cors = False if has_cors is None else has_cors
        token = data.get("token") or project_metadata.function.token
        methods = (
            project_metadata.function.methods
            if not data.get("methods") and project_metadata
            else data.get("methods")
        )

        adapter_url, adapter_data = get_argo_input_adapter(
            client=client,
            network=network,
            frie_label=project_metadata.project.local_label,
            argo_adapter_port=argo_adapter_port,
            is_raw=is_raw,
            token=token,
            methods=methods,
            has_cors=has_cors,
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


class GetContainerKeyStep(PipelineStep):
    def execute(self, data):
        if data.get("container_key"):
            return data

        project_metadata = data["project_metadata"]
        data["container_key"] = project_metadata.project.local_label
        return data


class RemoveNonDeployableFilesStep(PipelineStep):
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

        node_modules_path = project_path / "node_modules"
        if node_modules_path.exists() and node_modules_path.is_dir():
            shutil.rmtree(node_modules_path)

        return data


class GetFRIEContainerTargetStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        project_metadata = data["project_metadata"]
        container_manager = data["container_manager"]
        function_image_name = data["function_image_name"]
        network = data["network"]
        is_raw = data.get("is_raw")
        if project_metadata and is_raw is None:
            is_raw = project_metadata.function.is_raw
        is_raw = False if is_raw is None else is_raw
        timeout = data.get("timeout")
        if project_metadata and not timeout:
            timeout = project_metadata.function.timeout
        language = project_metadata.project.language

        label = project_metadata.project.local_label
        argo_target_port = engine_settings.CONTAINER.ARGO.INTERNAL_TARGET_PORT.split(
            "/"
        )[0]
        target_url = f"http://{engine_settings.HOST_BIND}:{argo_target_port}/{label}"
        frie_container_manager(
            container_manager=container_manager,
            project_path=project_path,
            network=network,
            image_name=function_image_name,
            label=label,
            language=language,
            is_raw=is_raw,
            timeout=timeout,
            target_url=target_url,
        )

        data["local_label"] = label
        data["target_url"] = f"URL: {target_url}"
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
        data["local_label"] = f"\n Local label: {container_key}"
        return data


class RestartFunctionStep(PipelineStep):
    def execute(self, data):
        container_key = data["container_key"]
        container_manager = data["container_manager"]

        container_manager.restart(
            f"{engine_settings.CONTAINER.FRIE.LABEL_KEY}={container_key}"
        )
        return data


class CleanFunctionsStep(PipelineStep):
    def execute(self, data):
        client = data["client"]
        container_manager = data["container_manager"]

        for container in container_manager.list(
            label=engine_settings.CONTAINER.FRIE.LABEL_KEY
        ):
            container.stop()
            container.remove()

        for container in container_manager.list(
            label=engine_settings.CONTAINER.ARGO.LABEL_KEY
        ):
            container.stop()
            container.remove()

        for image in client.client.images.list():
            prefix = f"{engine_settings.HUB_USERNAME}/{engine_settings.HUB_PREFFIX}"
            if any(tag.startswith(prefix) for tag in image.tags):
                client.client.images.remove(image.id, force=True)

        for network in client.client.networks.list():
            prefix_name = engine_settings.CONTAINER.NETWORK_NAME
            if network.name.startswith(prefix_name):
                network.remove()
        return data
