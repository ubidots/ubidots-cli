from pathlib import Path

import httpx
import typer

from cli.commons.enums import MessageColorEnum
from cli.commons.pipelines import Pipeline
from cli.commons.utils import exit_with_error_message
from cli.functions import FUNCTION_API_ROUTES
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.exceptions import ContainerAlreadyRunningException
from cli.functions.engines.exceptions import ContainerExecutionException
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
from cli.functions.helpers import argo_container_manager
from cli.functions.helpers import ensure_project_integrity
from cli.functions.helpers import frie_container_manager
from cli.functions.helpers import get_argo_input_adapter
from cli.functions.helpers import get_or_create_network
from cli.functions.helpers import prepare_handler_file
from cli.functions.helpers import save_manifest_project_file
from cli.functions.helpers import verify_and_fetch_images
from cli.functions.pipelines import BuildEndpointStep
from cli.functions.pipelines import CheckResponseStep
from cli.functions.pipelines import CompressProjectStep
from cli.functions.pipelines import ConfirmOverwriteStep
from cli.functions.pipelines import CreateProjectFolderStep
from cli.functions.pipelines import DownloadFileStep
from cli.functions.pipelines import ExtractProjectStep
from cli.functions.pipelines import ExtractTemplateStep
from cli.functions.pipelines import GetClientStep
from cli.functions.pipelines import GetContainerManagerStep
from cli.functions.pipelines import GetFunctionLogsStep
from cli.functions.pipelines import GetFunctionStatusStep
from cli.functions.pipelines import HttpGetRequestStep
from cli.functions.pipelines import PrintColoredTableStep
from cli.functions.pipelines import PrintkeyStep
from cli.functions.pipelines import SaveManifestStep
from cli.functions.pipelines import StopFunctionStep
from cli.functions.pipelines import UploadFileStep
from cli.functions.pipelines import ValidateProjectStep
from cli.functions.pipelines import ValidateTemplateStep


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
    steps = [
        ValidateTemplateStep(),
        CreateProjectFolderStep(),
        ExtractTemplateStep(),
        SaveManifestStep(),
    ]
    pipeline = Pipeline(
        steps, success_message=f"Project '{name}' created in '{project_path}'."
    )
    pipeline.run(
        {
            "project_path": project_path,
            "language": language,
            "runtime": runtime,
        }
    )


def start_function(
    engine: FunctionEngineTypeEnum,
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
    label = info_project.label

    typer.echo("")
    typer.echo("  ------------------")
    typer.echo("  Starting Function:")
    typer.echo("  ------------------")
    typer.echo(f"  Name: {info_project.name}")
    typer.echo(f"  Runtime: {info_project.runtime}")
    typer.echo(f"  Local label: {label}")
    typer.echo("")
    typer.echo("   -------")
    typer.echo("   INPUTS:")
    typer.echo("   -------")
    typer.echo(f"   Raw: {raw}")
    typer.echo(f"   Method: {method}")
    typer.echo(f"   Token: {token if token else None}")
    typer.echo("")

    try:
        container, argo_adapter_port = argo_container_manager(
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

    ip_address = container.attrs["NetworkSettings"]["Networks"][
        engine_settings.CONTAINER.NETWORK_NAME
    ]["IPAddress"]
    adapter_url, data = get_argo_input_adapter(
        client=client,
        network=network,
        label=label,
        frie_container_name=label,
        argo_adapter_port=argo_adapter_port,
        raw=raw,
        ip_address=ip_address,
        token=token,
    )
    http_client = httpx.Client(follow_redirects=True)
    http_client.post(adapter_url, json=data)

    prepare_handler_file(current_path, info_project.language)
    argo_target_port = engine_settings.CONTAINER.ARGO.INTERNAL_TARGET_PORT.split("/")[0]
    target_url = f"http://{ip_address}:{argo_target_port}/{label}"
    try:
        frie_container_manager(
            container_manager=container_manager,
            current_path=current_path,
            network=network,
            image_name=function_image_name,
            label=label,
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
    steps = [
        GetClientStep(engine=engine),
        GetContainerManagerStep(),
        StopFunctionStep(),
    ]
    pipeline = Pipeline(
        steps, success_message=f"Function '{label}' stoped successfully."
    )
    pipeline.run({"project_path": Path.cwd(), "container_key": label})


def status_function(engine: FunctionEngineTypeEnum):
    steps = [
        GetClientStep(engine=engine),
        GetContainerManagerStep(),
        GetFunctionStatusStep(),
        PrintColoredTableStep(key="status"),
    ]
    pipeline = Pipeline(steps)
    pipeline.run({})


def logs_function(
    engine: FunctionEngineTypeEnum, label: str, tail: str, follow: bool, remote: bool
):
    if remote:
        steps = [
            ValidateProjectStep(),
            BuildEndpointStep(FUNCTION_API_ROUTES["logs"]),
            HttpGetRequestStep(),
            CheckResponseStep(),
            PrintColoredTableStep(key="results"),
        ]
        pipeline = Pipeline(steps)
        pipeline.run({"project_path": Path.cwd()})
    else:
        steps = [
            GetClientStep(engine=engine),
            GetContainerManagerStep(),
            GetFunctionLogsStep(tail=tail, follow=follow),
            PrintkeyStep(key="logs"),
        ]
        pipeline = Pipeline(steps)
        pipeline.run({"container_key": label})


def push_function(confirm: bool = False):
    steps = [
        ValidateProjectStep(),
        ConfirmOverwriteStep(
            confirm=confirm,
            message="Are you sure you want to overwrite the remote files?",
        ),
        CompressProjectStep(),
        BuildEndpointStep(FUNCTION_API_ROUTES["zip_file"]),
        UploadFileStep(),
        CheckResponseStep(),
    ]
    pipeline = Pipeline(steps, success_message="Function uploaded successfully.")
    pipeline.run({"project_path": Path.cwd()})


def pull_function(confirm: bool = False):
    steps = [
        ValidateProjectStep(),
        ConfirmOverwriteStep(
            confirm=confirm,
            message="Are you sure you want to overwrite the local files?",
        ),
        BuildEndpointStep(FUNCTION_API_ROUTES["zip_file"]),
        DownloadFileStep(),
        CheckResponseStep(),
        ExtractProjectStep(),
    ]
    pipeline = Pipeline(steps, success_message="Function downloaded successfully.")
    pipeline.run({"project_path": Path.cwd()})
