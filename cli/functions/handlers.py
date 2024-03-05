import json
import zipfile
from contextlib import suppress
from io import BytesIO
from json import JSONDecodeError
from pathlib import Path

import typer
from docker.errors import NotFound

from cli.commons.enums import HTTPMethodEnum
from cli.commons.enums import MessageColorEnum
from cli.commons.exceptions import HttpMaxAttemptsRequestException
from cli.commons.exceptions import HttpRequestException
from cli.commons.styles import print_colored_table
from cli.commons.utils import build_endpoint
from cli.commons.utils import perform_http_request
from cli.commons.utils import show_error_and_exit
from cli.functions.engines.enums import ContainerStatusEnum
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.enums import TargetTypeEnum
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
from cli.functions.helpers import find_available_ports
from cli.functions.helpers import generate_local_function_label
from cli.functions.helpers import get_or_create_network
from cli.functions.helpers import save_manifest_project_file
from cli.functions.helpers import verify_and_fetch_images
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

    language_str = language
    template_file = settings.FUNCTIONS.TEMPLATES_PATH / f"{language_str}.zip"
    if not template_file.exists():
        typer.echo(f"Template for '{language_str}' not found at '{template_file}'.")
        raise typer.Exit(1)

    try:
        project_path.mkdir(parents=True, exist_ok=False)
        with zipfile.ZipFile(template_file, "r") as zip_ref:
            zip_ref.extractall(project_path)
        save_manifest_project_file(
            project_path=project_path, label="", language=language, runtime=runtime
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

    engine_manager = FunctionEngineClientManager(engine=engine)
    client = engine_manager.get_client()

    # function_image_name = (
    #     f"{engine_settings.HUB_USERNAME}/{project_metadata.project.runtime.value}"
    # )
    function_image_name = f"{engine_settings.HUB_USERNAME}/python3.9-base:latest"
    argo_image_name = f"{engine_settings.HUB_USERNAME}/argo2:2.0.1"
    try:
        verify_and_fetch_images(
            client=client, image_names=[function_image_name, argo_image_name]
        )
    except (
        EngineNotInstalledException,
        ImageNotFoundException,
        ImageFetchException,
    ) as error:
        show_error_and_exit(error=error)

    network = get_or_create_network(client=client)
    container_manager = client.get_container_manager()

    info_project = project_metadata.project
    if label := info_project.label:
        try:
            rie_container = container_manager.get(label=label)
            if rie_container and rie_container.status == ContainerStatusEnum.RUNNING:
                typer.echo(
                    typer.style(
                        f"* The function with label '{label}' is already running.\n",
                        fg=MessageColorEnum.WARNING,
                        bold=True,
                    )
                )
                raise typer.Exit(1)
        except ContainerNotFoundException:
            pass

    label_value = (
        info_project.label
        if info_project.label
        else generate_local_function_label(name=info_project.name)
    )
    save_manifest_project_file(
        project_path=current_path,
        engine=engine,
        label=label_value,
        language=info_project.language,
        runtime=info_project.runtime,
        raw=raw,
        method=method,
        token=token,
        cors=cors,
        cron=cron,
        timeout=timeout,
    )

    try:
        frie_container = container_manager.start(
            image_name=function_image_name,
            labels={engine_settings.CONTAINER.KEY: label_value},
            ports={engine_settings.CONTAINER.FRIE.INTERNAL_PORT: (host, port)},
            volumes={str(current_path): engine_settings.CONTAINER.FRIE.VOLUME_MAPPING},
            network_name=network.name,
        )
    except (
        ContainerAlreadyRunningException,
        ContainerExecutionException,
    ) as error:
        show_error_and_exit(error=error)

    typer.echo("")
    typer.echo("  ------------------")
    typer.echo("  Starting Function:")
    typer.echo("  ------------------")
    typer.echo(f"  Name: {info_project.name}")
    typer.echo(f"  Language: {info_project.language}")
    typer.echo(f"  Runtime: {info_project.runtime}")
    typer.echo(f"  Main File: {info_project.main_file}")
    typer.echo(f"  Local Function label: {label_value}")
    typer.echo("")
    typer.echo("   -------")
    typer.echo("   INPUTS:")
    typer.echo("   -------")
    typer.echo(f"   Port: {port}")
    typer.echo(f"   Raw: {raw}")
    typer.echo(f"   Method: {method}")
    typer.echo(f"   Token: {token}")
    typer.echo(f"   Cors: {cors}")
    typer.echo(f"   Cron: {cron}")
    typer.echo(f"   Timeout: {timeout}")
    typer.echo("")

    argo_container = None
    with suppress(NotFound):
        argo_container = client.client.containers.get(
            engine_settings.CONTAINER.ARGO.NAME
        )
        if argo_container and argo_container.status in [
            ContainerStatusEnum.PAUSED,
            ContainerStatusEnum.EXITED,
        ]:
            argo_container.restart()
        argo_adapter_port = next(
            iter(
                argo_container.ports.get(
                    engine_settings.CONTAINER.ARGO.INTERNAL_ADAPTER_PORT, []
                )
            ),
            {},
        ).get("HostPort")

    if not argo_container:
        argo_adapter_port, argo_taget_port = find_available_ports(
            ports=[
                engine_settings.CONTAINER.ARGO.EXTERNAL_ADAPTER_PORT,
                engine_settings.CONTAINER.ARGO.EXTERNAL_TARGET_PORT,
            ]
        )
        try:
            argo_container = container_manager.start(
                image_name=argo_image_name,
                container_name=engine_settings.CONTAINER.ARGO.NAME,
                labels={
                    engine_settings.CONTAINER.KEY: engine_settings.CONTAINER.ARGO.NAME
                },
                ports={
                    engine_settings.CONTAINER.ARGO.INTERNAL_ADAPTER_PORT: (
                        host,
                        argo_adapter_port,
                    ),
                    engine_settings.CONTAINER.ARGO.INTERNAL_TARGET_PORT: (
                        host,
                        argo_taget_port,
                    ),
                },
                network_name=network.name,
            )
        except (
            ContainerAlreadyRunningException,
            ContainerExecutionException,
        ) as error:
            show_error_and_exit(error=error)

    network_manager = client.get_network_manager()
    network = network_manager.get(network.id)

    frie_ip_address = network.attrs["Containers"][frie_container.id][
        "IPv4Address"
    ].split("/")[0]
    frie_port = engine_settings.CONTAINER.FRIE.INTERNAL_PORT.split("/")[0]

    url = f"http://{host}:{argo_adapter_port}/{engine_settings.CONTAINER.ARGO.API_ADAPTER_BASE_PATH}"
    data = {
        "label": label_value,
        "path": label_value,
        "is_strict": True,
        "middlewares": [],
        "target": {
            "type": (
                TargetTypeEnum.RIE_FUNCTION_RAW.value
                if raw
                else TargetTypeEnum.RIE_FUNCTION.value
            ),
            "url": f"http://{frie_ip_address}:{frie_port}{engine_settings.CONTAINER.FRIE.API_INVOKE_BASE_PATH}",
            "auth_token": token,
        },
    }
    try:
        perform_http_request(method=HTTPMethodEnum.POST, url=url, json=data)
    except (HttpRequestException, HttpMaxAttemptsRequestException) as error:
        show_error_and_exit(error=error)

    typer.echo(
        typer.style(
            f"* Function '{label_value}' started successfully!\n",
            fg=MessageColorEnum.SUCCESS,
            bold=True,
        )
    )


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
        payload_obj = json.loads(payload)
    except (TypeError, JSONDecodeError) as error:
        show_error_and_exit(error=error)

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

    info_project = project_metadata.project
    save_manifest_project_file(
        project_path=current_path,
        engine=engine,
        label=info_project.label,
        language=info_project.language,
        runtime=info_project.runtime,
        payload=payload_obj,
    )

    engine_manager = FunctionEngineClientManager(engine=engine)
    client = engine_manager.get_client()

    argo_container = None
    with suppress(NotFound):
        argo_container = client.client.containers.get(
            engine_settings.CONTAINER.ARGO.NAME
        )

    install_command = ["/bin/sh", "-c", "apt-get update && apt-get install -y curl"]
    _, output = argo_container.exec_run(install_command, user="root")

    url = f"http://localhost:8042/{label}"
    command = f"curl -s {url}"
    _, output = argo_container.exec_run(command)
    typer.echo(output.decode("utf8"))


def push_function(confirm: bool):
    actual_path = Path.cwd()
    try:
        project_metadata, _ = ensure_project_integrity(
            project_path=actual_path,
            validation_flags={
                FunctionProjectValidationTypeEnum.MANIFEST_FILE: True,
                FunctionProjectValidationTypeEnum.MAIN_FILE_PRESENCE: True,
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
    try:
        response = perform_http_request(
            method=HTTPMethodEnum.POST, url=url, headers=headers, files=files
        )
        typer.echo(response.json()["message"])
    except HttpRequestException as error:
        show_error_and_exit(error=error)


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
    try:
        response = perform_http_request(
            method=HTTPMethodEnum.GET, url=url, headers=headers
        )
    except HttpRequestException as error:
        show_error_and_exit(error=error)

    with zipfile.ZipFile(BytesIO(response.content), "r") as zip_ref:
        zip_ref.extractall(actual_path)
    typer.echo("Function downloaded successfully.")
