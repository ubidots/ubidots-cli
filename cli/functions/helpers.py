import io
import os
import zipfile
from pathlib import Path
from typing import IO

import yaml
from docker import DockerClient
from pydantic import ValidationError

from cli.functions.enums import FunctionLanguageEnum
from cli.functions.enums import FunctionNodejsRuntimeLayerTypeEnum
from cli.functions.enums import FunctionPythonRuntimeLayerTypeEnum
from cli.functions.models import FunctionInfo
from cli.functions.models import FunctionProjectInfo
from cli.functions.models import FunctionProjectMetadata
from cli.settings import settings


def save_manifest_project_file(
    project_path: Path,
    language: FunctionLanguageEnum,
    runtime: FunctionPythonRuntimeLayerTypeEnum | FunctionNodejsRuntimeLayerTypeEnum,
    function_id: str | None = None,
) -> None:
    metadata = FunctionProjectMetadata(
        project=FunctionProjectInfo(
            name=project_path.name, language=language, runtime=runtime
        ),
        function=FunctionInfo(id=function_id),
    )
    metadata_file = project_path / settings.FUNCTIONS.PROJECT_METADATA_FILE
    with open(metadata_file, "w") as file:
        yaml.dump(metadata.for_yaml_dump(), file)


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

    try:
        return FunctionProjectMetadata(**manifest_data)
    except ValidationError as error:
        error_message = f"Error in '{manifest_file}' format: {error}"
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


def stop_and_remove_container_by_label(
    docker_client: DockerClient, label: str, status: str = "running"
):
    existing_containers = docker_client.containers.list(filters={"label": label})
    for existing_container in existing_containers:
        if existing_container.status == status:
            existing_container.stop()
            existing_container.remove()
        else:
            existing_container.remove()
