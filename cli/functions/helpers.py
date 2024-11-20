import io
import os
import shutil
import socket
import zipfile
from contextlib import suppress
from pathlib import Path
from typing import IO
from typing import Any

import httpx
import typer
import yaml
from docker.errors import APIError
from docker.errors import NotFound
from docker.models.containers import Container
from docker.models.networks import Network
from pydantic import ValidationError

from cli.commons.enums import MessageColorEnum
from cli.functions.engines.docker.client import FunctionDockerClient
from cli.functions.engines.docker.container import \
    FunctionDockerContainerManager
from cli.functions.engines.enums import ArgoMethodEnum
from cli.functions.engines.enums import ContainerStatusEnum
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.enums import TargetTypeEnum
from cli.functions.engines.exceptions import ContainerNotFoundException
from cli.functions.engines.exceptions import EngineNotInstalledException
from cli.functions.engines.exceptions import ImageFetchException
from cli.functions.engines.exceptions import ImageNotFoundException
from cli.functions.engines.models import ArgoAdapterBaseModel
from cli.functions.engines.models import \
    ArgoAdapterMiddlewareAllowedMethodsBaseModel
from cli.functions.engines.models import ArgoAdapterMiddlewareCorsBaseModel
from cli.functions.engines.models import ArgoAdapterTargetBaseModel
from cli.functions.engines.podman.client import FunctionPodmanClient
from cli.functions.engines.podman.container import \
    FunctionPodmanContainerManager
from cli.functions.engines.settings import engine_settings
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.enums import FunctionMethodEnum
from cli.functions.enums import FunctionNodejsRuntimeLayerTypeEnum
from cli.functions.enums import FunctionPythonRuntimeLayerTypeEnum
from cli.functions.enums import FunctionRuntimeLayerTypeEnum
from cli.functions.models import FunctionGlobals
from cli.functions.models import FunctionInfo
from cli.functions.models import FunctionProjectInfo
from cli.functions.models import FunctionProjectMetadata
from cli.settings import settings


def build_functions_payload(**kwargs) -> dict:
    data = {
        "triggers": kwargs.get("triggers", {}),
        "serverless": kwargs.get("serverless", {}),
        "environment": kwargs.get("environment", []),
    }
    if label := kwargs.get("label"):
        data["label"] = label
    if name := kwargs.get("name"):
        data["name"] = name

    return data


def save_manifest_project_file(
    project_path: Path,
    language: FunctionLanguageEnum,
    runtime: (
        FunctionRuntimeLayerTypeEnum
        | FunctionPythonRuntimeLayerTypeEnum
        | FunctionNodejsRuntimeLayerTypeEnum
    ),
    local_label: str = "",
    engine: FunctionEngineTypeEnum = engine_settings.CONTAINER.DEFAULT_ENGINE,
    function_id: str = "",
    **kwargs,
) -> None:
    globals_instance = FunctionGlobals(engine=engine)
    project_instance = FunctionProjectInfo(
        name=project_path.name,
        language=language,
        runtime=runtime,
        local_label=local_label,
    )
    function_instance = FunctionInfo(
        id=function_id,
        **kwargs,
    )

    metadata = FunctionProjectMetadata(
        globals=globals_instance,
        project=project_instance,
        function=function_instance,
    )

    metadata_file = project_path / settings.FUNCTIONS.PROJECT_METADATA_FILE
    with open(metadata_file, "w") as file:
        yaml.dump(metadata.to_yaml_serializable_format(), file)


def read_manifest_project_file(project_path: Path) -> FunctionProjectMetadata:
    manifest_file = settings.FUNCTIONS.PROJECT_METADATA_FILE
    manifest_file_path = project_path / manifest_file

    if not manifest_file_path.exists():
        error_message = (
            f"'{manifest_file}' not found. Are you in the correct project directory?"
        )
        raise FileNotFoundError(error_message)

    with open(manifest_file_path) as file:
        manifest_data = yaml.safe_load(file)

    if manifest_data is None:
        error_message = (
            f"The '{manifest_file}' is empty, make sure it has the correct structure."
        )
        raise ValueError(error_message)

    try:
        return FunctionProjectMetadata(**manifest_data)
    except ValidationError as error:
        error_message = f"Invalid input in '{manifest_file}' file for "
        for err in error.errors():
            error_message += f"'{'.'.join([str(loc) for loc in err['loc'][0:2]])}' -> {err['msg']} | "
        raise ValueError(error_message) from error


def compress_project_to_zip(
    project_path: Path, exclude_files: list[str] | None = None
) -> IO[bytes]:
    exclude_files = [] if exclude_files is None else exclude_files
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(project_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, project_path)

                if not any(Path(arcname).match(pattern) for pattern in exclude_files):
                    zipf.write(file_path, arcname)

            for folder in os.listdir(root):
                folder_path = os.path.join(root, folder)
                if os.path.isdir(folder_path):
                    arcname = os.path.relpath(folder_path, project_path)

                    if not any(
                        Path(arcname).match(pattern) for pattern in exclude_files
                    ):
                        zipf.write(folder_path, arcname=arcname)
    zip_buffer.seek(0)
    return zip_buffer


def enumerate_project_files(project_path: Path) -> list[Path]:
    return [
        Path(root) / file for root, _, files in os.walk(project_path) for file in files
    ]


def verify_and_fetch_images(
    client: FunctionDockerClient | FunctionPodmanClient, image_names: list[str]
) -> None:
    validator = client.get_validator()
    for image_name in image_names:
        try:
            validator.validate_engine_installed()
        except EngineNotInstalledException as error:
            raise error
        downloader = client.get_downloader()
        try:
            downloader.pull_image(image_name=image_name)
        except (ImageNotFoundException, ImageFetchException) as error:
            raise error


def create_handler_file(project_path: Path, language: FunctionLanguageEnum):
    extension = FunctionLanguageEnum(language).handler_extension
    handler_file = f"{settings.FUNCTIONS.DEFAULT_HANDLER_FILE_NAME}.{extension}"
    template_path = settings.FUNCTIONS.HANDLERS_PATH / handler_file
    handler_path = project_path / handler_file
    shutil.copy(template_path, handler_path)
    return handler_path


def get_or_create_network(
    client: FunctionDockerClient | FunctionPodmanClient,
) -> object:
    network_manager = client.get_network_manager()
    networks = network_manager.list()
    network = next(iter(networks), None)
    if not network:
        network = network_manager.create()
    return network


def is_port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(("localhost", port)) != 0


def find_available_ports(
    ports: list[int],
    start_range: int = engine_settings.DEFAULT_START_PORT_RANGE,
    end_range: int = engine_settings.DEFAULT_END_PORT_RANGE,
) -> list[int]:
    available_ports = []
    fallback_needed = len(ports)

    for port in ports:
        if is_port_available(port):
            available_ports.append(port)
            fallback_needed -= 1

    # If not all requested ports are available, find fallback ports
    if fallback_needed > 0:
        for port in range(start_range, end_range + 1):
            if len(available_ports) == len(ports):
                break  # Stop when we have enough ports
            if is_port_available(port):
                available_ports.append(port)

    return available_ports


def get_external_container_port(container: Container, internal_port: int) -> int:
    port_info: dict[str, Any] = next(iter(container.ports.get(internal_port, [])), {})
    return int(port_info.get("HostPort", 0))


def frie_container_manager(
    container_manager: FunctionDockerContainerManager | FunctionPodmanContainerManager,
    project_path: Path,
    network: Network,
    image_name: str,
    label: str,
    language: FunctionLanguageEnum,
    is_raw: bool,
    timeout: int,
    target_url: str,
):
    def check_container_status() -> object | None:
        if not label:
            return None

        container = None
        with suppress(ContainerNotFoundException):
            container = container_manager.get(label=label)

        if container is None:
            return None

        if container.status == ContainerStatusEnum.RUNNING:
            message = f"* The function with label '{label}' is already running.\n"
            styled_message = typer.style(
                message, fg=MessageColorEnum.WARNING, bold=True
            )
            typer.echo(styled_message)
            raise typer.Exit(1)

        return container

    container = check_container_status()
    if container is None:
        port = engine_settings.CONTAINER.FRIE.EXTERNAL_PORT
        if not is_port_available(port=port):
            port = find_available_ports(ports=[port])

        volumes = {
            str(project_path): engine_settings.CONTAINER.FRIE.VOLUME_MAPPING,
        }
        environment = {"AWS_LAMBDA_FUNCTION_TIMEOUT": str(timeout)}
        if language == FunctionLanguageEnum.NODEJS:
            volumes["node_modules"] = {"bind": "/var/task/node_modules", "mode": "ro"}

        container = container_manager.start(
            image_name=image_name,
            container_name=label,
            network_name=network.name,
            labels={
                engine_settings.CONTAINER.FRIE.LABEL_KEY: label,
                engine_settings.CONTAINER.FRIE.IS_RAW_LABEL_KEY: str(is_raw),
                engine_settings.CONTAINER.FRIE.URL_LABEL_KEY: target_url,
            },
            volumes=volumes,
            environment=environment,
            command=f"{settings.FUNCTIONS.DEFAULT_HANDLER_FILE_NAME}.{settings.FUNCTIONS.DEFAULT_HANDLER_FUNCTION_NAME}",
            hostname=label,
        )


def argo_container_manager(
    container_manager: FunctionDockerContainerManager | FunctionPodmanContainerManager,
    client: FunctionDockerClient | FunctionPodmanClient,
    network: Network,
    image_name: str,
    frie_label: str,
):
    container_name = engine_settings.CONTAINER.ARGO.NAME

    def check_container_status() -> object | None:
        container = None
        with suppress(NotFound):
            container = client.client.containers.get(container_name)

        if container is None:
            return None

        if container.status in [ContainerStatusEnum.PAUSED, ContainerStatusEnum.EXITED]:
            try:
                container.restart()
            except APIError:
                container.remove()
                return None

            return container

        if container.status == ContainerStatusEnum.RUNNING:
            argo_adapter_port = get_external_container_port(
                container=container,
                internal_port=engine_settings.CONTAINER.ARGO.INTERNAL_ADAPTER_PORT,
            )
            ip_address = container.attrs["NetworkSettings"]["Networks"][network.name][
                "IPAddress"
            ]
            url = f"http://{ip_address}:{argo_adapter_port}/{engine_settings.CONTAINER.ARGO.API_ADAPTER_BASE_PATH}/~{frie_label}"
            response = httpx.get(url)
            if response.status_code == httpx.codes.OK:
                httpx.delete(url)

        return container

    container = check_container_status()
    if container is None:
        argo_adapter_port, argo_target_port = find_available_ports(
            ports=[
                engine_settings.CONTAINER.ARGO.EXTERNAL_ADAPTER_PORT,
                engine_settings.CONTAINER.ARGO.EXTERNAL_TARGET_PORT,
            ]
        )
        container = container_manager.start(
            image_name=image_name,
            container_name=container_name,
            network_name=network.name,
            labels={engine_settings.CONTAINER.ARGO.LABEL_KEY: container_name},
            ports={
                engine_settings.CONTAINER.ARGO.INTERNAL_ADAPTER_PORT: (
                    engine_settings.HOST_BIND,
                    argo_adapter_port,
                ),
                engine_settings.CONTAINER.ARGO.INTERNAL_TARGET_PORT: (
                    engine_settings.HOST_BIND,
                    argo_target_port,
                ),
            },
            hostname=engine_settings.CONTAINER.ARGO.HOSTNAME,
        )
    else:
        argo_adapter_port = get_external_container_port(
            container=container,
            internal_port=engine_settings.CONTAINER.ARGO.INTERNAL_ADAPTER_PORT,
        )
    return container, argo_adapter_port


def get_argo_input_adapter(
    client: FunctionDockerClient | FunctionPodmanClient,
    network: Network,
    frie_label: str,
    argo_adapter_port: int,
    is_raw: bool,
    token: str,
    methods: list[FunctionMethodEnum],
    has_cors: bool,
) -> tuple[str, dict]:
    network_manager = client.get_network_manager()
    network = network_manager.get(network.id)

    frie_port = engine_settings.CONTAINER.FRIE.INTERNAL_PORT.split("/")[0]
    url = f"http://{engine_settings.HOST_BIND}:{argo_adapter_port}/{engine_settings.CONTAINER.ARGO.API_ADAPTER_BASE_PATH}"
    argo_methods = [ArgoMethodEnum(method.value) for method in methods]
    if has_cors:
        argo_methods.append(ArgoMethodEnum.OPTIONS)

    middlewares: list[
        ArgoAdapterMiddlewareAllowedMethodsBaseModel
        | ArgoAdapterMiddlewareCorsBaseModel
    ] = [
        ArgoAdapterMiddlewareAllowedMethodsBaseModel(
            methods=argo_methods,
        )
    ]
    if has_cors:
        middlewares.append(ArgoAdapterMiddlewareCorsBaseModel())

    data = ArgoAdapterBaseModel(
        label=frie_label,
        path=frie_label,
        middlewares=middlewares,
        target=ArgoAdapterTargetBaseModel(
            type=(
                TargetTypeEnum.RIE_FUNCTION_RAW
                if is_raw
                else TargetTypeEnum.RIE_FUNCTION
            ),
            url=f"http://{frie_label}:{frie_port}{engine_settings.CONTAINER.FRIE.API_INVOKE_BASE_PATH}",
            auth_token=token,
        ),
    )
    return url, data.model_dump()
