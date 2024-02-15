import json
import zipfile
from io import BytesIO
from json import JSONDecodeError
from pathlib import Path

import typer
from docker import DockerClient

from cli.commons.enums import HTTPMethodEnum
from cli.commons.utils import build_endpoint
from cli.commons.utils import perform_http_request
from cli.functions.engines.enums import FunctionEngineServeEnum
from cli.functions.engines.exceptions import EngineNotInstalledException
from cli.functions.engines.exceptions import ImageFetchException
from cli.functions.engines.exceptions import ImageNotFoundException
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.enums import FunctionMethodEnum
from cli.functions.enums import FunctionNodejsRuntimeLayerTypeEnum
from cli.functions.enums import FunctionProjectValidationTypeEnum
from cli.functions.enums import FunctionPythonRuntimeLayerTypeEnum
from cli.functions.exceptions import DockerContainerAlreadyRunningError
from cli.functions.exceptions import DockerContainerExecutionError
from cli.functions.exceptions import DockerHostPortError
from cli.functions.helpers import compress_project_to_zip
from cli.functions.helpers import ensure_image_availability
from cli.functions.helpers import ensure_project_integrity
from cli.functions.helpers import manage_container
from cli.functions.helpers import save_manifest_project_file
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


def start_function(
    engine: FunctionEngineServeEnum,
    host: str,
    port: int,
    raw: bool,
    method: FunctionMethodEnum,
    token: str,
    cors: bool,
    cron: str,
    timeout: int,
):
    current_path = Path.cwd()
    try:
        project_metadata, _ = ensure_project_integrity(
            project_path=current_path,
            validation_flags={
                FunctionProjectValidationTypeEnum.MANIFEST_FILE: True,
            },
        )
    except (FileNotFoundError, ValueError) as error:
        typer.echo(error)
        raise typer.Exit(1) from error

    docker_client = DockerClient.from_env()
    image_name = f"{settings.FUNCTIONS.DOCKER_CONFIG.HUB_USERNAME}/{project_metadata.project.runtime.value}"

    try:
        ensure_image_availability(client=docker_client, image_name=image_name)
    except (
        EngineNotInstalledException,
        ImageNotFoundException,
        ImageFetchException,
    ) as error:
        typer.echo(error)
        raise typer.Exit(1) from error
    typer.echo("Docker image is now up-to-date locally.")

    try:
        container = manage_container(
            client=docker_client,
            image_name=image_name,
            current_path=current_path,
            project_name=project_metadata.project.name,
            host_port=port,
        )
        typer.echo(f"Container started successfully on port {port}: {container.id}")
    except (
        DockerContainerAlreadyRunningError,
        DockerHostPortError,
        DockerContainerExecutionError,
    ) as error:
        typer.echo(error)
        raise typer.Exit(1) from error
    typer.echo("Function successfully executed inside the container.")


def run_function(host_port: int, payload: str):
    current_path = Path.cwd()
    try:
        project_metadata, _ = ensure_project_integrity(
            project_path=current_path,
            validation_flags={
                FunctionProjectValidationTypeEnum.MANIFEST_FILE: True,
            },
        )
    except (FileNotFoundError, ValueError) as error:
        typer.echo(error)
        raise typer.Exit(1) from error

    docker_client = DockerClient.from_env()
    image_name = f"{settings.FUNCTIONS.DOCKER_CONFIG.HUB_USERNAME}/{project_metadata.project.runtime.value}"

    try:
        ensure_image_availability(client=docker_client, image_name=image_name)
    except (
        EngineNotInstalledException,
        ImageNotFoundException,
        ImageFetchException,
    ) as error:
        typer.echo(error)
        raise typer.Exit(1) from error

    try:
        manage_container(
            client=docker_client,
            image_name=image_name,
            current_path=current_path,
            project_name=project_metadata.project.name,
            host_port=host_port,
            is_exec_function=True,
        )
    except (
        DockerContainerAlreadyRunningError,
        DockerHostPortError,
        DockerContainerExecutionError,
    ) as error:
        typer.echo(error)
        raise typer.Exit(1) from error

    try:
        json.loads(payload)
    except (TypeError, JSONDecodeError) as error:
        typer.echo(error)
        raise typer.Exit(1) from error

    url = f"http://{settings.FUNCTIONS.DOCKER_CONFIG.HOST}:{host_port}{settings.FUNCTIONS.DOCKER_CONFIG.RIE_INVOCATION_PATH}"
    response = perform_http_request(method=HTTPMethodEnum.POST, url=url, json=payload)
    typer.echo(response.json())


def push_function(confirm: bool):
    actual_path = Path.cwd()
    try:
        project_metadata, _ = ensure_project_integrity(
            project_path=actual_path, run_all_validations=True
        )
    except (FileNotFoundError, ValueError) as error:
        typer.echo(error)
        raise typer.Exit(1) from error

    if not confirm:
        confirm = project_metadata.globals.auto_overwrite
    if not confirm and not typer.confirm(
        "Are you sure you want to overwrite the local files?"
    ):
        raise typer.Abort

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


def pull_function(confirm: bool):
    actual_path = Path.cwd()
    try:
        project_metadata, _ = ensure_project_integrity(
            project_path=actual_path,
            validation_flags={
                FunctionProjectValidationTypeEnum.MANIFEST_FILE: True,
            },
        )
    except (FileNotFoundError, ValueError) as error:
        typer.echo(error)
        raise typer.Exit(1) from error

    if not confirm:
        confirm = project_metadata.globals.auto_overwrite
    if not confirm and not typer.confirm(
        "Are you sure you want to overwrite the local files?"
    ):
        raise typer.Abort

    url, headers = build_endpoint(
        route="/api/-/functions/{function_key}/zip-file/",
        function_key=project_metadata.function.id,
    )
    response = perform_http_request(method=HTTPMethodEnum.GET, url=url, headers=headers)

    with zipfile.ZipFile(BytesIO(response.content), "r") as zip_ref:
        zip_ref.extractall(actual_path)
    typer.echo("Function downloaded successfully.")
