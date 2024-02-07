import zipfile
from io import BytesIO
from pathlib import Path

import typer
from docker import DockerClient
from docker import errors as docker_errors

from cli.commons.enums import HTTPMethodEnum
from cli.commons.utils import build_endpoint
from cli.commons.utils import perform_http_request
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.enums import FunctionNodejsRuntimeLayerTypeEnum
from cli.functions.enums import FunctionPythonRuntimeLayerTypeEnum
from cli.functions.exceptions import DockerImageNotAvailableLocallyError
from cli.functions.exceptions import DockerImageNotFoundError
from cli.functions.exceptions import DockerNotInstalledError
from cli.functions.helpers import compress_project_to_zip
from cli.functions.helpers import save_manifest_project_file
from cli.functions.helpers import stop_and_remove_container_by_label
from cli.functions.validators import FunctionDockerValidator
from cli.functions.validators import FunctionProjectValidator
from cli.functions.validators import ProjectValidationDataManager
from cli.settings import settings


def create_function(
    name: str,
    language: FunctionLanguageEnum,
    runtime: FunctionPythonRuntimeLayerTypeEnum | FunctionNodejsRuntimeLayerTypeEnum,
):
    project_path = Path.cwd() / name if not Path(name).is_absolute() else Path(name)
    if project_path.exists():
        typer.echo(f"A folder named '{name}' already exists.")
        raise typer.Exit(1)

    language_str = language.value
    template_file = settings.FUNCTIONS.TEMPLATES_PATH / f"{language_str}.zip"
    if not template_file.exists():
        typer.echo(f"Template for '{language_str}' not found at '{template_file}'.")
        raise typer.Exit(1)

    try:
        project_path.mkdir(parents=True, exist_ok=False)
        with zipfile.ZipFile(template_file, "r") as zip_ref:
            zip_ref.extractall(project_path)
        save_manifest_project_file(
            project_path=project_path, language=language, runtime=runtime
        )
        typer.echo(f"Project {name} created in '{project_path}'.")

    except PermissionError as error:
        typer.echo(f"Permission denied: {error}.")
        raise typer.Exit(1) from error


def init_function(host_port: int):
    actual_path = Path.cwd()
    try:
        project_data_manager = ProjectValidationDataManager(project_path=actual_path)
        project_metadata, project_files = project_data_manager.prepare_data()
        validator = FunctionProjectValidator(
            project_metadata=project_metadata, project_files=project_files
        )
        validator.validate_manifest_file()
    except (FileNotFoundError, ValueError) as error:
        typer.echo(error)
        raise typer.Exit(1) from error

    docker_client = DockerClient.from_env()
    image_name = f"{settings.FUNCTIONS.DOCKER_CONFIG.HUB_USERNAME}/{project_metadata.project.runtime.value}"
    docker_validator = FunctionDockerValidator(
        docker_client=docker_client, image_name=image_name
    )
    try:
        docker_validator.validate_docker_is_installed()
        try:
            docker_validator.validate_image_available_locally()
        except DockerImageNotAvailableLocallyError:
            docker_validator.validate_image_available_on_dockerhub()
    except (DockerNotInstalledError, DockerImageNotFoundError) as error:
        typer.echo(error)
        raise typer.Exit(1) from error
    typer.echo("Docker image is now up-to-date locally.")

    container_label_key = settings.FUNCTIONS.DOCKER_CONFIG.CONTAINER_LABEL
    container_label_value = (
        f"{container_label_key}_{project_metadata.project.name}_{image_name}"
    )
    stop_and_remove_container_by_label(
        docker_client=docker_client, label=container_label_key
    )
    try:
        container = docker_client.containers.run(
            image_name,
            labels={container_label_key: container_label_value},
            volumes={str(actual_path): settings.FUNCTIONS.DOCKER_CONFIG.VOLUME_MAPPING},
            ports={f"{settings.FUNCTIONS.DOCKER_CONFIG.CONTAINER_PORT}/tcp": host_port},
            detach=settings.FUNCTIONS.DOCKER_CONFIG.IS_DETACH,
        )
        typer.echo(
            f"Container started successfully on port {host_port}: {container.id}"
        )
    except docker_errors.APIError as error:
        typer.echo(
            "Try specifying a different host port using the '--host-port' option "
            f"or free up the port '{host_port}'."
        )
        raise typer.Exit(1) from error
    except docker_errors.ContainerError as error:
        typer.echo(f"Error executing the container: {error}")
        raise typer.Exit(1) from error
    typer.echo("Function successfully executed inside the container.")


def push_function():
    actual_path = Path.cwd()
    try:
        project_data_manager = ProjectValidationDataManager(project_path=actual_path)
        project_metadata, project_files = project_data_manager.prepare_data()
        validator = FunctionProjectValidator(
            project_metadata=project_metadata, project_files=project_files
        )
        validator.run_all_validations()
        typer.echo(
            "Project validation successful. Preparing for the next step in the update process..."
        )
    except (FileNotFoundError, ValueError) as error:
        typer.echo(error)
        raise typer.Exit(1) from error

    zip_file_obj = compress_project_to_zip(actual_path)
    typer.echo("Project successfully compressed into a ZIP file, ready for upload.")

    url, headers = build_endpoint(
        route="/api/-/functions/{function_key}/zip-file/",
        function_key=project_metadata.function.id,
    )
    files = {
        "zipFile": (
            f"{project_metadata.project.name}.zip",
            zip_file_obj,
            "application/zip",
        )
    }
    response = perform_http_request(
        method=HTTPMethodEnum.POST, url=url, headers=headers, files=files
    )
    typer.echo(response.json()["message"])


def pull_function():
    actual_path = Path.cwd()
    try:
        project_data_manager = ProjectValidationDataManager(project_path=actual_path)
        project_metadata, project_files = project_data_manager.prepare_data()
        validator = FunctionProjectValidator(
            project_metadata=project_metadata, project_files=project_files
        )
        validator.validate_manifest_file()
    except (FileNotFoundError, ValueError) as error:
        typer.echo(error)
        raise typer.Exit(1) from error

    url, headers = build_endpoint(
        route="/api/-/functions/{function_key}/zip-file/",
        function_key=project_metadata.function.id,
    )
    response = perform_http_request(method=HTTPMethodEnum.GET, url=url, headers=headers)

    with zipfile.ZipFile(BytesIO(response.content), "r") as zip_ref:
        zip_ref.extractall(actual_path)
    typer.echo("Function downloaded successfully.")
