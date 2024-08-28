from pathlib import Path

from cli.commons.pipelines import Pipeline
from cli.functions import FUNCTION_API_ROUTES
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.enums import FunctionMethodEnum
from cli.functions.enums import FunctionNodejsRuntimeLayerTypeEnum
from cli.functions.enums import FunctionPythonRuntimeLayerTypeEnum
from cli.functions.enums import FunctionRuntimeLayerTypeEnum
from cli.functions.pipelines import BuildEndpointStep
from cli.functions.pipelines import CheckResponseStep
from cli.functions.pipelines import CompressProjectStep
from cli.functions.pipelines import ConfirmOverwriteStep
from cli.functions.pipelines import CreateArgoContainerAdapterStep
from cli.functions.pipelines import CreateHandlerFRIEStep
from cli.functions.pipelines import CreateProjectFolderStep
from cli.functions.pipelines import DownloadFileStep
from cli.functions.pipelines import ExtractProjectStep
from cli.functions.pipelines import ExtractTemplateStep
from cli.functions.pipelines import GetArgoContainerInputAdapterStep
from cli.functions.pipelines import GetArgoContainerIPAddressStep
from cli.functions.pipelines import GetArgoContainerManagerStep
from cli.functions.pipelines import GetClientNetworkStep
from cli.functions.pipelines import GetClientStep
from cli.functions.pipelines import GetContainerManagerStep
from cli.functions.pipelines import GetFRIEContainerTargetStep
from cli.functions.pipelines import GetFunctionLogsStep
from cli.functions.pipelines import GetFunctionStatusStep
from cli.functions.pipelines import GetImageNamesStep
from cli.functions.pipelines import GetProjectFilesStep
from cli.functions.pipelines import HttpGetRequestStep
from cli.functions.pipelines import PrintColoredTableStep
from cli.functions.pipelines import PrintkeyStep
from cli.functions.pipelines import ReadManifestStep
from cli.functions.pipelines import RemoveHandlerFRIEStep
from cli.functions.pipelines import SaveManifestStep
from cli.functions.pipelines import ShowStartupInfoStep
from cli.functions.pipelines import StopFunctionStep
from cli.functions.pipelines import UploadFileStep
from cli.functions.pipelines import ValidateImageNamesStep
from cli.functions.pipelines import ValidateProjectStep
from cli.functions.pipelines import ValidateTemplateStep
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
            "template_file": settings.FUNCTIONS.TEMPLATES_PATH / f"{language}.zip",
            "language": language,
            "runtime": runtime,
        }
    )


def start_function(
    engine: FunctionEngineTypeEnum,
    methods: list[FunctionMethodEnum],
    raw: bool,
    token: str,
    cors: bool,
    cron: str,
    timeout: int,
):
    steps = [
        ReadManifestStep(),
        GetProjectFilesStep(),
        ValidateProjectStep(validate_manifest_file=False),
        GetClientStep(engine=engine),
        GetImageNamesStep(),
        ValidateImageNamesStep(),
        ShowStartupInfoStep(),
        GetContainerManagerStep(),
        GetClientNetworkStep(),
        GetArgoContainerManagerStep(),
        GetArgoContainerIPAddressStep(),
        GetArgoContainerInputAdapterStep(),
        CreateArgoContainerAdapterStep(),
        CreateHandlerFRIEStep(),
        GetFRIEContainerTargetStep(),
        SaveManifestStep(),
        PrintkeyStep(key="target_url"),
    ]
    pipeline = Pipeline(steps, success_message="Function started successfully.")
    pipeline.run(
        {
            "project_path": Path.cwd(),
            "function_kwargs": {
                "is_raw": raw,
                "methods": methods,
                "token": token,
                "cors": cors,
                "cron": cron,
                "timeout": timeout,
            },
        }
    )


def stop_function(
    engine: FunctionEngineTypeEnum,
    label: str,
):
    steps = [
        GetClientStep(engine=engine),
        GetContainerManagerStep(),
        RemoveHandlerFRIEStep(),
        StopFunctionStep(),
    ]
    pipeline = Pipeline(
        steps, success_message=f"Function '{label}' stoped successfully."
    )
    pipeline.run({"container_key": label})


def status_function(
    engine: FunctionEngineTypeEnum,
):
    steps = [
        GetClientStep(engine=engine),
        GetContainerManagerStep(),
        GetFunctionStatusStep(),
        PrintColoredTableStep(key="status"),
    ]
    pipeline = Pipeline(steps)
    pipeline.run({})


def logs_function(
    engine: FunctionEngineTypeEnum,
    label: str,
    tail: str,
    follow: bool,
    remote: bool,
):
    if remote:
        steps = [
            ReadManifestStep(),
            GetProjectFilesStep(),
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


def push_function(
    confirm: bool = False,
):
    steps = [
        ReadManifestStep(),
        GetProjectFilesStep(),
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


def pull_function(
    confirm: bool = False,
):
    steps = [
        ReadManifestStep(),
        GetProjectFilesStep(),
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
