import zipfile
from io import BytesIO
from pathlib import Path

import httpx
import typer

from cli.commons.enums import MessageColorEnum
from cli.commons.styles import print_colored_table
from cli.commons.utils import build_endpoint
from cli.commons.utils import check_response_status
from cli.commons.utils import exit_with_error_message
from cli.commons.utils import exit_with_success_message
from cli.functions import API_ROUTES as FUNCTION_API_ROUTES
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.exceptions import ContainerAlreadyRunningException
from cli.functions.engines.exceptions import ContainerExecutionException
from cli.functions.engines.exceptions import ContainerNotFoundException
from cli.functions.engines.exceptions import ContainerPortInUseException
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
from cli.functions.enums import FunctionRuntimeLayerTypeEnum
from cli.functions.exceptions import FolderAlreadyExistsException
from cli.functions.exceptions import PermissionDeniedException
from cli.functions.exceptions import TemplateNotFoundException
from cli.functions.helpers import argo_container_manager
from cli.functions.helpers import compress_project_to_zip
from cli.functions.helpers import ensure_project_integrity
from cli.functions.helpers import frie_container_manager
from cli.functions.helpers import generate_local_function_label
from cli.functions.helpers import get_argo_input_adapter
from cli.functions.helpers import get_or_create_network
from cli.functions.helpers import read_manifest_project_file
from cli.functions.helpers import save_manifest_project_file
from cli.functions.helpers import verify_and_fetch_images
from cli.settings import settings


def create_function(
    name: str,
    language: FunctionLanguageEnum,
    runtime: (
        FunctionRuntimeLayerTypeEnum
        | FunctionPythonRuntimeLayerTypeEnum
        | FunctionNodejsRuntimeLayerTypeEnum
    ),
):
    project_path = Path.cwd() / name if not Path(name).is_absolute() else Path(name)
    if project_path.exists():
        exit_with_error_message(exception=FolderAlreadyExistsException(name=name))

    template_file = settings.FUNCTIONS.TEMPLATES_PATH / f"{language}.zip"
    if not template_file.exists():
        exit_with_error_message(
            exception=TemplateNotFoundException(
                language=language, template_file=template_file
            )
        )

    try:
        project_path.mkdir(parents=True, exist_ok=False)
        with zipfile.ZipFile(template_file, "r") as zip_ref:
            zip_ref.extractall(project_path)
        save_manifest_project_file(
            project_path=project_path,
            engine=FunctionEngineTypeEnum.DOCKER,
            label="",
            language=language,
            runtime=runtime,
        )
        exit_with_success_message(
            message=f"Project '{name}' created in '{project_path}'."
        )
    except PermissionError as error:
        exit_with_error_message(exception=PermissionDeniedException(error=error))


def start_function(
    engine: FunctionEngineTypeEnum,
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
        project_metadata = ensure_project_integrity(
            project_path=current_path,
            validation_flags={
                FunctionProjectValidationTypeEnum.MAIN_FILE_PRESENCE: True,
            },
        )
    except (FileNotFoundError, ValueError) as error:
        exit_with_error_message(exception=error)
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
        exit_with_error_message(exception=error)

    network = get_or_create_network(client=client)
    container_manager = client.get_container_manager()
    info_project = project_metadata.project
    label = (
        info_project.label
        if info_project.label
        else generate_local_function_label(name=info_project.name)
    )

    typer.echo("")
    typer.echo("  ------------------")
    typer.echo("  Starting Function:")
    typer.echo("  ------------------")
    typer.echo(f"  Name: {info_project.name}")
    typer.echo(f"  Language: {info_project.language}")
    typer.echo(f"  Runtime: {info_project.runtime}")
    typer.echo(f"  Main File: {info_project.main_file}")
    typer.echo(f"  Local label: {label}")
    typer.echo("")
    typer.echo("   -------")
    typer.echo("   INPUTS:")
    typer.echo("   -------")
    typer.echo(f"   Port: {port}")
    typer.echo(f"   Raw: {raw}")
    typer.echo(f"   Method: {method}")
    typer.echo(f"   Token: {token}")
    typer.echo("")

    try:
        _, argo_adapter_port = argo_container_manager(
            container_manager=container_manager,
            client=client,
            network=network,
            image_name=argo_image_name,
            label=label,
        )
    except (
        ContainerAlreadyRunningException,
        ContainerPortInUseException,
        ContainerExecutionException,
    ) as error:
        exit_with_error_message(exception=error)

    adapter_url, data = get_argo_input_adapter(
        client=client,
        network=network,
        label=label,
        frie_container_name=label,
        argo_adapter_port=argo_adapter_port,
        raw=raw,
        token=token,
    )

    client = httpx.Client(follow_redirects=True)
    client.post(adapter_url, json=data)

    argo_target_port = engine_settings.CONTAINER.ARGO.INTERNAL_TARGET_PORT.split("/")[0]
    target_url = f"http://{engine_settings.HOST}:{argo_target_port}/{label}"
    try:
        frie_container_manager(
            container_manager=container_manager,
            current_path=current_path,
            network=network,
            image_name=function_image_name,
            label=label,
            port=port,
            is_raw=raw,
            target_url=target_url,
        )
    except (
        ContainerAlreadyRunningException,
        ContainerPortInUseException,
        ContainerExecutionException,
    ) as error:
        exit_with_error_message(exception=error)

    save_manifest_project_file(
        project_path=current_path,
        engine=engine,
        label=label,
        language=info_project.language,
        runtime=info_project.runtime,
        raw=raw,
        method=method,
        token=token,
        cors=cors,
        cron=cron,
        timeout=timeout,
        url=target_url,
    )

    typer.echo("   -------")
    typer.echo("   OUTPUT:")
    typer.echo("   -------")
    typer.echo(f"   Url: {target_url}")
    typer.echo("")
    typer.echo(
        typer.style(
            f"> Function '{label}' started successfully!\n",
            fg=MessageColorEnum.SUCCESS,
            bold=True,
        )
    )


def stop_function(engine: FunctionEngineTypeEnum, label: str):
    if label == ".":
        current_path = Path.cwd()
        try:
            project_metadata = read_manifest_project_file(project_path=current_path)
        except (FileNotFoundError, ValueError) as error:
            exit_with_error_message(exception=error)

        label = project_metadata.project.label

    engine_manager = FunctionEngineClientManager(engine=engine)
    client = engine_manager.get_client()
    container_manager = client.get_container_manager()
    label_pair = f"{engine_settings.CONTAINER.FRIE.LABEL_KEY}={label}"
    try:
        container_manager.stop(label=label_pair)
        typer.echo(
            typer.style(
                f"> Function '{label}' stoped successfully\n",
                fg=MessageColorEnum.SUCCESS,
                bold=True,
            )
        )
    except ContainerNotFoundException as error:
        exit_with_error_message(exception=error)


def status_function(engine: FunctionEngineTypeEnum):
    engine_manager = FunctionEngineClientManager(engine=engine)
    client = engine_manager.get_client()
    container_manager = client.get_container_manager()
    container_status = container_manager.status(
        container_label_key=engine_settings.CONTAINER.FRIE.LABEL_KEY,
        is_raw_label_key=engine_settings.CONTAINER.FRIE.IS_RAW_LABEL_KEY,
        target_url_label_key=engine_settings.CONTAINER.FRIE.URL_LABEL_KEY,
    )
    print_colored_table(results=container_status)


def logs_function(engine: FunctionEngineTypeEnum, label: str, tail: str, follow: bool):
    engine_manager = FunctionEngineClientManager(engine=engine)
    client = engine_manager.get_client()
    container_manager = client.get_container_manager()
    label_pair = f"{engine_settings.CONTAINER.FRIE.LABEL_KEY}={label}"
    try:
        container_logs = container_manager.logs(
            label=label_pair, tail=tail, follow=follow
        )
    except ContainerNotFoundException as error:
        exit_with_error_message(exception=error)
    typer.echo(container_logs)


def push_function(confirm: bool = False):
    """
    This function pushes the current project to a remote server.

    Steps:
    1. Validate the project's integrity.
    2. Confirm overwriting remote files if necessary.
    3. Compress the project into a zip file.
    4. Build the endpoint URL and headers.
    5. Upload the zip file to the remote server.
    6. Check the response status.
    7. Exit with a success message.

    Parameters:
    confirm (bool) [default=False]: Indicates whether to bypass the overwrite confirmation prompt.
    """

    # Step 1: Validate the project's integrity.
    current_path = Path.cwd()
    try:
        project_metadata = ensure_project_integrity(
            project_path=current_path,
            validation_flags={
                FunctionProjectValidationTypeEnum.MANIFEST_FILE: True,
                FunctionProjectValidationTypeEnum.MAIN_FILE_PRESENCE: True,
            },
        )
    except (FileNotFoundError, ValueError) as error:
        exit_with_error_message(exception=error)

    # Step 2: Confirm overwriting remote files if necessary.
    confirm = confirm or project_metadata.globals.auto_overwrite
    if not confirm and not typer.confirm(
        "Are you sure you want to overwrite the remote files?"
    ):
        raise typer.Abort

    # Step 3: Compress the project into a zip file.
    zip_file_obj = compress_project_to_zip(current_path)

    # Step 4: Build the endpoint URL and headers.
    url, headers = build_endpoint(
        route=FUNCTION_API_ROUTES["zip_file"],
        function_key=project_metadata.function.id,
    )
    files = {
        "zipFile": (
            f"{project_metadata.project.name}.zip",
            zip_file_obj,
            "application/zip",
        )
    }

    # Step 5: Upload the zip file to the remote server.
    client = httpx.Client(follow_redirects=True)
    response = client.post(url=url, headers=headers, files=files)

    # Step 6: Check the response status.
    try:
        check_response_status(response=response)
    except httpx.RequestError as error:
        exit_with_error_message(exception=error)

    # Step 7: Exit with a success message.
    exit_with_success_message(message="Function uploaded successfully.")


def pull_function(confirm: bool = False):
    """
    This function pulls the current project from a remote server.

    Steps:
    1. Validate the project's integrity.
    2. Confirm overwriting local files if necessary.
    3. Build the endpoint URL and headers.
    4. Download the zip file from the remote server.
    5. Check the response status.
    6. Extract the zip file contents to the current directory.
    7. Exit with a success message.

    Parameters:
    confirm (bool) [default=False]: Indicates whether to bypass the overwrite confirmation prompt.
    """

    # Step 1: Validate the project's integrity.
    current_path = Path.cwd()
    try:
        project_metadata = ensure_project_integrity(
            project_path=current_path,
            validation_flags={
                FunctionProjectValidationTypeEnum.MANIFEST_FILE: True,
            },
        )
    except (FileNotFoundError, ValueError) as error:
        exit_with_error_message(exception=error)

    # Step 2: Confirm overwriting local files if necessary.
    confirm = confirm or project_metadata.globals.auto_overwrite
    if not confirm and not typer.confirm(
        "Are you sure you want to overwrite the local files?"
    ):
        raise typer.Abort

    # Step 3: Build the endpoint URL and headers.

    url, headers = build_endpoint(
        route=FUNCTION_API_ROUTES["zip_file"],
        function_key=project_metadata.function.id,
    )

    # Step 4: Download the zip file from the remote server.
    response = httpx.get(url, headers=headers)

    # Step 5: Check the response status.
    try:
        check_response_status(response=response)
    except httpx.RequestError as error:
        exit_with_error_message(exception=error)

    # Step 6: Extract the zip file contents to the current directory.
    with zipfile.ZipFile(BytesIO(response.content), "r") as zip_ref:
        zip_ref.extractall(current_path)

    # Step 7: Exit with a success message.
    exit_with_success_message(message="Function downloaded successfully.")
