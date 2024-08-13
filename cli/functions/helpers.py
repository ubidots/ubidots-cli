import io
import os
import socket
import zipfile
from contextlib import suppress
from pathlib import Path
from typing import IO

import httpx
import typer
import yaml
from docker.errors import APIError
from docker.errors import NotFound

from cli.commons.enums import MessageColorEnum
from cli.functions.engines.docker.client import FunctionDockerClient
from cli.functions.engines.docker.container import \
    FunctionDockerContainerManager
from cli.functions.engines.enums import ContainerStatusEnum
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.enums import TargetTypeEnum
from cli.functions.engines.exceptions import ContainerNotFoundException
from cli.functions.engines.exceptions import EngineNotInstalledException
from cli.functions.engines.exceptions import ImageFetchException
from cli.functions.engines.exceptions import ImageNotAvailableLocallyException
from cli.functions.engines.exceptions import ImageNotFoundException
from cli.functions.engines.models import ArgoAdapterBaseModel
from cli.functions.engines.models import ArgoAdapterTargetBaseModel
from cli.functions.engines.podman.client import FunctionPodmanClient
from cli.functions.engines.podman.container import \
    FunctionPodmanContainerManager
from cli.functions.engines.settings import engine_settings
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.enums import FunctionNodejsRuntimeLayerTypeEnum
from cli.functions.enums import FunctionProjectValidationTypeEnum
from cli.functions.enums import FunctionPythonRuntimeLayerTypeEnum
from cli.functions.models import FunctionGlobals
from cli.functions.models import FunctionInfo
from cli.functions.models import FunctionProjectInfo
from cli.functions.models import FunctionProjectMetadata
from cli.functions.validators import FunctionProjectValidator
from cli.settings import settings


def save_manifest_project_file(
    project_path: Path,
    engine: FunctionEngineTypeEnum,
    label: str,
    language: FunctionLanguageEnum,
    runtime: FunctionPythonRuntimeLayerTypeEnum | FunctionNodejsRuntimeLayerTypeEnum,
    function_id: str | None = None,
    auto_overwrite: bool = False,
    **kwargs,
) -> None:
    globals_instance = FunctionGlobals(engine=engine, auto_overwrite=auto_overwrite)
    project_instance = FunctionProjectInfo(
        name=project_path.name, label=label, language=language, runtime=runtime
    )
    function_instance = FunctionInfo(id=function_id, **kwargs)

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
    except ValueError as error:
        error_message = f"Invalid input in '{manifest_file}' file for "
        for err in error.errors():
            error_message += f"'{'.'.join(err['loc'][0:2])}' -> {err['msg']} | "
        raise ValueError(error_message) from error


def compress_project_to_zip(actual_path: Path) -> IO[bytes]:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(actual_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, actual_path)
                zipf.write(file_path, arcname)
            for folder in os.listdir(root):
                folder_path = os.path.join(root, folder)
                if os.path.isdir(folder_path):
                    arcname = os.path.relpath(folder_path, actual_path)
                    zipf.write(folder_path, arcname=arcname)
    zip_buffer.seek(0)
    return zip_buffer


def enumerate_project_files(project_path: Path) -> list[Path]:
    return [
        Path(root) / file for root, _, files in os.walk(project_path) for file in files
    ]


def ensure_project_integrity(
    project_path: Path,
    validation_flags: dict[FunctionProjectValidationTypeEnum, bool],
) -> FunctionProjectMetadata:
    try:
        project_metadata = read_manifest_project_file(project_path)
        project_files = enumerate_project_files(project_path)
        validator = FunctionProjectValidator(
            project_metadata=project_metadata,
            project_files=project_files,
            project_path=project_path,
            validation_flags=validation_flags,
        )
        validator.run_validations()
        return project_metadata
    except (FileNotFoundError, ValueError) as error:
        raise error


def verify_and_fetch_images(
    client: FunctionDockerClient | FunctionPodmanClient, image_names: list[str]
) -> None:
    validator = client.get_validator()
    for image_name in image_names:
        try:
            validator.validate_engine_installed()
            validator.validate_image_available_locally(image_name=image_name)
        except EngineNotInstalledException as error:
            raise error
        except ImageNotAvailableLocallyException:
            downloader = client.get_downloader()
            try:
                downloader.pull_image(image_name=image_name)
            except (ImageNotFoundException, ImageFetchException) as error:
                raise error


def get_or_create_network(
    client: FunctionDockerClient | FunctionPodmanClient,
) -> object | None:
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


def get_external_container_port(container: object, internal_port: int) -> int:
    return next(iter(container.ports.get(internal_port, [])), {}).get("HostPort")


def frie_container_manager(
    container_manager: FunctionDockerContainerManager | FunctionPodmanContainerManager,
    current_path: Path,
    network: object,
    image_name: str,
    label: str,
    is_raw: bool,
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

        container = container_manager.start(
            image_name=image_name,
            container_name=label,
            labels={
                engine_settings.CONTAINER.FRIE.LABEL_KEY: label,
                engine_settings.CONTAINER.FRIE.IS_RAW_LABEL_KEY: str(is_raw),
                engine_settings.CONTAINER.FRIE.URL_LABEL_KEY: target_url,
            },
            ports={
                engine_settings.CONTAINER.FRIE.INTERNAL_PORT: port,
            },
            volumes={str(current_path): engine_settings.CONTAINER.FRIE.VOLUME_MAPPING},
            network_name=network.name,
        )


def argo_container_manager(
    container_manager: FunctionDockerContainerManager | FunctionPodmanContainerManager,
    client: FunctionDockerClient | FunctionPodmanClient,
    network: object,
    image_name: str,
    label: str,
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
            ip_address = container.attrs["NetworkSettings"]["Networks"][
                engine_settings.CONTAINER.NETWORK_NAME
            ]["IPAddress"]
            url = f"http://{ip_address}:{argo_adapter_port}/{engine_settings.CONTAINER.ARGO.API_ADAPTER_BASE_PATH}/~{label}"
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
            labels={engine_settings.CONTAINER.ARGO.LABEL_KEY: container_name},
            ports={
                engine_settings.CONTAINER.ARGO.INTERNAL_ADAPTER_PORT: argo_adapter_port,
                engine_settings.CONTAINER.ARGO.INTERNAL_TARGET_PORT: argo_target_port,
            },
            network_name=network.name,
        )
    else:
        argo_adapter_port = get_external_container_port(
            container=container,
            internal_port=engine_settings.CONTAINER.ARGO.INTERNAL_ADAPTER_PORT,
        )
    return container, argo_adapter_port


def get_argo_input_adapter(
    client: FunctionDockerClient | FunctionPodmanClient,
    network: object,
    label: str,
    frie_container_name: str,
    argo_adapter_port: int,
    raw: bool,
    ip_address: str,
    token: str | None,
) -> tuple[str, dict]:
    network_manager = client.get_network_manager()
    network = network_manager.get(network.id)

    frie_port = engine_settings.CONTAINER.FRIE.INTERNAL_PORT.split("/")[0]
    url = f"http://{ip_address}:{argo_adapter_port}/{engine_settings.CONTAINER.ARGO.API_ADAPTER_BASE_PATH}"
    data = ArgoAdapterBaseModel(
        label=label,
        path=label,
        target=ArgoAdapterTargetBaseModel(
            type=(
                TargetTypeEnum.RIE_FUNCTION_RAW if raw else TargetTypeEnum.RIE_FUNCTION
            ),
            url=f"http://{frie_container_name}:{frie_port}{engine_settings.CONTAINER.FRIE.API_INVOKE_BASE_PATH}",
            auth_token=token,
        ),
    )
    return url, data.model_dump()
