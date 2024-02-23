import json
import zipfile
from io import BytesIO
from json import JSONDecodeError
from pathlib import Path

import typer

from cli.commons.enums import HTTPMethodEnum
from cli.commons.enums import MessageColorEnum
from cli.commons.styles import print_colored_table
from cli.commons.utils import build_endpoint
from cli.commons.utils import perform_http_request
from cli.commons.utils import show_error_and_exit
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.exceptions import ContainerAlreadyRunningException
from cli.functions.engines.exceptions import ContainerExecutionException
from cli.functions.engines.exceptions import ContainerNotFoundException
from cli.functions.engines.exceptions import EngineNotInstalledException
from cli.functions.engines.exceptions import ImageFetchException
from cli.functions.engines.exceptions import ImageNotFoundException
from cli.functions.engines.manager import FunctionEngineClientManager
from cli.functions.engines.settings import engine_settings
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.enums import FunctionMethodEnum
from cli.functions.enums import FunctionNodejsRuntimeLayerTypeEnum
from cli.functions.enums import FunctionProjectValidationTypeEnum
from cli.functions.enums import FunctionPythonRuntimeLayerTypeEnum
from cli.functions.helpers import compress_project_to_zip
from cli.functions.helpers import ensure_project_integrity
from cli.functions.helpers import generate_local_function_label
from cli.functions.helpers import save_manifest_project_file
from cli.functions.helpers import verify_and_fetch_image
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
    engine: FunctionEngineTypeEnum,
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
                FunctionProjectValidationTypeEnum.MAIN_FILE_PRESENCE: True,
            },
        )
    except (FileNotFoundError, ValueError) as error:
        show_error_and_exit(error=error)

    image_name = (
        f"{engine_settings.HUB_USERNAME}/{project_metadata.project.runtime.value}"
    )
    engine_manager = FunctionEngineClientManager(engine=engine)
    client = engine_manager.get_client()
    container_manager = client.get_container_manager()

    try:
        verify_and_fetch_image(client=client, image_name=image_name)
    except (
        EngineNotInstalledException,
        ImageNotFoundException,
        ImageFetchException,
    ) as error:
        show_error_and_exit(error=error)

    info_project = project_metadata.project
    label_value = generate_local_function_label(name=info_project.name)

    try:
        container = container_manager.start(
            image_name=image_name,
            labels={engine_settings.CONTAINER_KEY: label_value},
            volumes={str(current_path): engine_settings.VOLUME_MAPPING},
            ports={f"{engine_settings.CONTAINER_PORT}": (host, port)},
        )
        typer.echo("")
        typer.echo("  -------------------")
        typer.echo("  Starting function: ")
        typer.echo("  -------------------")
        typer.echo(f"  Name: {info_project.name}")
        typer.echo(f"  Runtime: {info_project.runtime.value}")
        typer.echo(f"  Local Function label: {label_value}")
        typer.echo(f"  Local Function ID: {container.id}")
        typer.echo("")
        typer.echo(
            typer.style(
                f"* Function started successfully on ({host}:{port})\n",
                fg=MessageColorEnum.SUCCESS,
                bold=True,
            )
        )
    except (
        ContainerAlreadyRunningException,
        ContainerExecutionException,
    ) as error:
        show_error_and_exit(error=error)


def stop_function(engine: FunctionEngineTypeEnum, label: str):
    engine_manager = FunctionEngineClientManager(engine=engine)
    client = engine_manager.get_client()
    container_manager = client.get_container_manager()
    try:
        container_manager.stop(label=label)
        typer.echo(
            typer.style(
                f"* Function '{label}' stoped successfully\n",
                fg=MessageColorEnum.SUCCESS,
                bold=True,
            )
        )
    except ContainerNotFoundException as error:
        show_error_and_exit(error=error)


def status_function(engine: FunctionEngineTypeEnum):
    engine_manager = FunctionEngineClientManager(engine=engine)
    client = engine_manager.get_client()
    container_manager = client.get_container_manager()
    container_status = container_manager.status()
    print_colored_table(results=container_status)


def logs_function(engine: FunctionEngineTypeEnum, label: str, tail: str, follow: bool):
    engine_manager = FunctionEngineClientManager(engine=engine)
    client = engine_manager.get_client()
    container_manager = client.get_container_manager()
    try:
        container_logs = container_manager.logs(label=label, tail=tail, follow=follow)
    except ContainerNotFoundException as error:
        show_error_and_exit(error=error)
    typer.echo(container_logs)


def run_function(
    engine: FunctionEngineTypeEnum, label: str, host: str, port: int, payload: str
):
    try:
        json.loads(payload)
    except (TypeError, JSONDecodeError) as error:
        show_error_and_exit(error=error)

    engine_manager = FunctionEngineClientManager(engine=engine)
    client = engine_manager.get_client()
    container_manager = client.get_container_manager()
    container_manager.reload(label=label)

    url = f"http://{host}:{port}{engine_settings.RIE_INVOCATION_PATH}"
    response = perform_http_request(method=HTTPMethodEnum.POST, url=url, json=payload)
    typer.echo(response.json())


def push_function(confirm: bool):
    actual_path = Path.cwd()
    try:
        project_metadata, _ = ensure_project_integrity(
            project_path=actual_path, run_all_validations=True
        )
    except (FileNotFoundError, ValueError) as error:
        show_error_and_exit(error=error)

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
        show_error_and_exit(error=error)

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
