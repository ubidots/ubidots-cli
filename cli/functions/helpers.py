import io
import os
import zipfile
from pathlib import Path
from typing import IO

import yaml
from docker.models.containers import Container

from cli.functions.engines.docker.client import FunctionDockerClient
from cli.functions.engines.exceptions import EngineNotInstalledException
from cli.functions.engines.exceptions import ImageFetchException
from cli.functions.engines.exceptions import ImageNotAvailableLocallyException
from cli.functions.engines.exceptions import ImageNotFoundException
from cli.functions.engines.podman.client import FunctionPodmanClient
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
    language: FunctionLanguageEnum,
    runtime: FunctionPythonRuntimeLayerTypeEnum | FunctionNodejsRuntimeLayerTypeEnum,
    function_id: str | None = None,
    auto_overwrite: bool = False,
) -> None:
    metadata = FunctionProjectMetadata(
        globals=FunctionGlobals(auto_overwrite=auto_overwrite),
        project=FunctionProjectInfo(
            name=project_path.name, language=language, runtime=runtime
        ),
        function=FunctionInfo(id=function_id),
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
    run_all_validations: bool = False,
    validation_flags: dict[FunctionProjectValidationTypeEnum, bool] | None = None,
) -> tuple[FunctionProjectMetadata, list[Path]]:
    try:
        project_metadata = read_manifest_project_file(project_path)
        project_files = enumerate_project_files(project_path)
        validator = FunctionProjectValidator(
            project_metadata=project_metadata,
            project_files=project_files,
            project_path=project_path,
            run_all_validations=run_all_validations,
            validation_flags=validation_flags,
        )
        validator.run_validations()
        return project_metadata, project_files
    except (FileNotFoundError, ValueError) as error:
        raise error


def verify_and_fetch_image(
    client: FunctionDockerClient | FunctionPodmanClient, image_name: str
) -> None:
    validator = client.get_validator()
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


def manage_container(
    client: FunctionDockerClient | FunctionPodmanClient,
    image_name: str,
    current_path: Path,
    project_name: str,
    host: str,
    port: int,
) -> Container:
    container_label_value = f"{settings.FUNCTIONS.DOCKER_CONFIG.CONTAINER_LABEL_PREFIX}_{project_name}_{image_name}"
    container = client.get_container()
    return container.run(
        image_name,
        labels={settings.FUNCTIONS.DOCKER_CONFIG.CONTAINER_KEY: container_label_value},
        volumes={str(current_path): settings.FUNCTIONS.DOCKER_CONFIG.VOLUME_MAPPING},
        ports={f"{settings.FUNCTIONS.DOCKER_CONFIG.CONTAINER_PORT}": (host, port)},
        detach=settings.FUNCTIONS.DOCKER_CONFIG.IS_DETACH,
    )
