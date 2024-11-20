from pathlib import Path

from cli.commons.pipelines import Pipeline
from cli.functions import FUNCTION_API_ROUTES
from cli.functions import pipelines
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.enums import FunctionMethodEnum
from cli.functions.enums import FunctionNodejsRuntimeLayerTypeEnum
from cli.functions.enums import FunctionPythonRuntimeLayerTypeEnum
from cli.functions.enums import FunctionRuntimeLayerTypeEnum
from cli.settings import settings


def create_function(
    name: str,
    language: FunctionLanguageEnum,
    runtime: (
        FunctionRuntimeLayerTypeEnum
        | FunctionPythonRuntimeLayerTypeEnum
        | FunctionNodejsRuntimeLayerTypeEnum
    ),
    methods: list[FunctionMethodEnum],
    is_raw: bool,
    cron: str,
    cors: bool,
    verbose: bool,
):
    project_path = Path.cwd() / name if not Path(name).is_absolute() else Path(name)
    steps = [
        pipelines.ValidateTemplateStep(),
        pipelines.CreateProjectFolderStep(),
        pipelines.ExtractTemplateStep(),
        pipelines.SaveManifestStep(),
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
            "is_raw": is_raw,
            "methods": methods,
            "has_cors": cors,
            "cron": cron,
            "verbose": verbose,
            "root": create_function.__name__,
        }
    )


def start_function(
    engine: FunctionEngineTypeEnum,
    methods: list[FunctionMethodEnum] | None,
    is_raw: bool | None,
    token: str,
    cors: bool | None,
    cron: str,
    timeout: int,
    verbose: bool,
):
    steps = [
        pipelines.ReadManifestStep(),
        pipelines.GetProjectFilesStep(),
        pipelines.ValidateProjectStep(),
        pipelines.GetClientStep(engine=engine),
        pipelines.GetImageNamesStep(),
        pipelines.ValidateImageNamesStep(),
        pipelines.ShowStartupInfoStep(),
        pipelines.GetContainerManagerStep(),
        pipelines.GetClientNetworkStep(),
        pipelines.GetArgoContainerManagerStep(),
        pipelines.GetArgoContainerInputAdapterStep(),
        pipelines.CreateArgoContainerAdapterStep(),
        pipelines.CreateHandlerFRIEStep(),
        pipelines.GetFRIEContainerTargetStep(),
        pipelines.SaveManifestStep(),
        pipelines.PrintkeyStep(key="target_url"),
    ]
    pipeline = Pipeline(steps, success_message="Function started successfully.")
    pipeline.run(
        {
            "project_path": Path.cwd(),
            "validations": {
                "manifest_file_exists": True,
                "function_exists": False,
            },
            "is_raw": is_raw,
            "methods": methods,
            "has_cors": cors,
            "token": token,
            "cron": cron,
            "timeout": timeout,
            "verbose": verbose,
            "root": start_function.__name__,
        }
    )


def stop_function(
    engine: FunctionEngineTypeEnum,
    label: str,
    verbose: bool,
):
    steps = [
        pipelines.GetClientStep(engine=engine),
        pipelines.GetContainerManagerStep(),
        pipelines.ReadManifestStep(),
        pipelines.GetContainerKeyStep(),
        pipelines.RemoveNonDeployableFilesStep(),
        pipelines.StopFunctionStep(),
        pipelines.PrintkeyStep(key="local_label"),
    ]
    pipeline = Pipeline(steps, success_message="Function stoped successfully.")
    pipeline.run(
        {
            "project_path": Path.cwd(),
            "container_key": label,
            "verbose": verbose,
            "root": stop_function.__name__,
        }
    )


def restart_function(
    engine: FunctionEngineTypeEnum,
    verbose: bool,
):
    steps = [
        pipelines.GetClientStep(engine=engine),
        pipelines.GetContainerManagerStep(),
        pipelines.ReadManifestStep(),
        pipelines.GetContainerKeyStep(),
        pipelines.RestartFunctionStep(),
    ]
    pipeline = Pipeline(steps, success_message="Function restarted successfully.")
    pipeline.run(
        {
            "project_path": Path.cwd(),
            "verbose": verbose,
            "root": restart_function.__name__,
        }
    )


def status_function(
    engine: FunctionEngineTypeEnum,
    verbose: bool,
):
    steps = [
        pipelines.GetClientStep(engine=engine),
        pipelines.GetContainerManagerStep(),
        pipelines.GetFunctionStatusStep(),
        pipelines.PrintColoredTableStep(key="status"),
    ]
    pipeline = Pipeline(steps)
    pipeline.run({"verbose": verbose, "root": status_function.__name__})


def logs_function(
    engine: FunctionEngineTypeEnum,
    label: str,
    tail: str,
    follow: bool,
    remote: bool,
    verbose: bool,
):
    if remote:
        steps = [
            pipelines.ReadManifestStep(),
            pipelines.GetProjectFilesStep(),
            pipelines.ValidateProjectStep(),
            pipelines.BuildEndpointStep(FUNCTION_API_ROUTES["logs"]),
            pipelines.HttpGetRequestStep(),
            pipelines.CheckResponseStep(),
            pipelines.PrintColoredTableStep(key="results"),
        ]
        pipeline = Pipeline(steps)
        pipeline.run(
            {
                "project_path": Path.cwd(),
                "validations": {
                    "manifest_file_exists": True,
                    "function_exists": True,
                },
                "verbose": verbose,
                "root": logs_function.__name__,
            }
        )
    else:
        steps = [
            pipelines.GetClientStep(engine=engine),
            pipelines.GetContainerManagerStep(),
            pipelines.GetFunctionLogsStep(tail=tail, follow=follow),
            pipelines.PrintkeyStep(key="logs"),
        ]
        pipeline = Pipeline(steps)
        pipeline.run(
            {
                "container_key": label,
                "verbose": verbose,
                "root": logs_function.__name__,
            }
        )


def push_function(
    confirm: bool,
    verbose: bool,
):
    steps = [
        pipelines.ReadManifestStep(),
        pipelines.GetProjectFilesStep(),
        pipelines.ValidateProjectStep(),
        pipelines.ConfirmOverwriteStep(),
        pipelines.BuildEndpointStep(FUNCTION_API_ROUTES["base"]),
        pipelines.CreateFunctionStep(),
        pipelines.SaveManifestStep(),
        pipelines.BuildEndpointStep(FUNCTION_API_ROUTES["detail"]),
        pipelines.UpdateFunctionStep(),
        pipelines.ReadManifestStep(),
        pipelines.CompressProjectStep(),
        pipelines.BuildEndpointStep(FUNCTION_API_ROUTES["zip_file"]),
        pipelines.UploadFileStep(),
        pipelines.CheckResponseStep(),
    ]
    pipeline = Pipeline(steps, success_message="Function uploaded successfully.")
    pipeline.run(
        {
            "project_path": Path.cwd(),
            "overwrite": {
                "confirm": confirm,
                "message": "Are you sure you want to overwrite the remote files?",
            },
            "validations": {
                "manifest_file_exists": True,
                "function_exists": True,
            },
            "verbose": verbose,
            "root": push_function.__name__,
        }
    )


def pull_function(
    confirm: bool,
    verbose: bool,
):
    steps = [
        pipelines.ReadManifestStep(),
        pipelines.GetProjectFilesStep(),
        pipelines.ValidateProjectStep(),
        pipelines.ConfirmOverwriteStep(),
        pipelines.BuildEndpointStep(FUNCTION_API_ROUTES["zip_file"]),
        pipelines.DownloadFileStep(),
        pipelines.CheckResponseStep(),
        pipelines.ExtractProjectStep(),
    ]
    pipeline = Pipeline(steps, success_message="Function downloaded successfully.")
    pipeline.run(
        {
            "project_path": Path.cwd(),
            "overwrite": {
                "confirm": confirm,
                "message": "Are you sure you want to overwrite the local files?",
            },
            "validations": {
                "manifest_file_exists": True,
                "function_exists": True,
            },
            "verbose": verbose,
            "root": pull_function.__name__,
        }
    )


def clean_functions(
    engine: FunctionEngineTypeEnum,
    confirm: bool,
    verbose: bool,
):
    steps = [
        pipelines.ConfirmOverwriteStep(),
        pipelines.GetClientStep(engine=engine),
        pipelines.GetContainerManagerStep(),
        pipelines.CleanFunctionsStep(),
    ]
    pipeline = Pipeline(steps)
    pipeline.run(
        {
            "overwrite": {
                "confirm": confirm,
                "message": (
                    "Are you sure you want to proceed?\n"
                    "This will remove all unused images, containers, and networks, which cannot be undone."
                ),
            },
            "verbose": verbose,
            "root": clean_functions.__name__,
        }
    )
