from pathlib import Path

from cli.commons.enums import OutputFormatFieldsEnum
from cli.commons.pipelines import Pipeline
from cli.commons.utils import sanitize_function_name
from cli.functions import FUNCTION_API_ROUTES
from cli.functions import pipelines
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.enums import FunctionMethodEnum
from cli.functions.enums import FunctionRuntimeLayerTypeEnum
from cli.settings import settings


def create_function(
    name: str,
    language: FunctionLanguageEnum,
    runtime: FunctionRuntimeLayerTypeEnum,
    methods: list[FunctionMethodEnum],
    is_raw: bool,
    engine: FunctionEngineTypeEnum,
    cron: str,
    cors: bool,
    verbose: bool,
    timeout: int,
    created_at: str,
    profile: str,
    token: str = "",
    function_id: str = "",
    params: str = "{}",
    has_cors: bool = settings.FUNCTIONS.DEFAULT_HAS_CORS,
    is_secure: bool = settings.FUNCTIONS.DEFAULT_IS_SECURE,
    http_enabled: bool = settings.FUNCTIONS.DEFAULT_HTTP_ENABLED,
):
    label = sanitize_function_name(name)
    project_path = Path.cwd() / name if not Path(name).is_absolute() else Path(name)
    steps = [
        pipelines.ValidateNotInExistingFunctionDirectoryStep(),
        pipelines.ValidateAllowedRuntimeStep(),
        pipelines.ValidateRuntimeAgaisntLanguageStep(),
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
            "profile": profile,
            "name": name,
            "template_file": settings.FUNCTIONS.TEMPLATES_PATH / f"{language}.zip",
            "language": language,
            "runtime": runtime,
            "methods": methods,
            "label": label,
            "function_id": function_id,
            "cron": cron,
            "has_cron": cron != "",
            "has_cors": cors,
            "is_raw": is_raw,
            "timeout": timeout,
            "params": params,
            "engine": engine,
            "token": token,
            "http_has_cors": has_cors,
            "http_is_secure": is_secure,
            "http_enabled": http_enabled,
            "created_at": created_at,
            "root": create_function.__name__,
            "verbose": verbose,
        }
    )


def start_function(
    verbose: bool,
):
    steps = [
        pipelines.ReadManifestStep(),
        pipelines.GetProjectFilesStep(),
        pipelines.ValidateProjectStep(),
        pipelines.GetClientStep(),
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
        pipelines.PrintkeyStep(key="target_url"),
    ]
    pipeline = Pipeline(steps, success_message="Function started successfully.")
    pipeline.run(
        {
            "project_path": Path.cwd(),
            "validations": {
                "manifest_file": True,
                "function_exists": False,
            },
            "verbose": verbose,
            "root": start_function.__name__,
        }
    )


def stop_function(
    verbose: bool,
):
    steps = [
        pipelines.ReadManifestStep(),
        pipelines.GetClientStep(),
        pipelines.GetContainerManagerStep(),
        pipelines.GetContainerKeyStep(),
        pipelines.RemoveNonDeployableFilesStep(),
        pipelines.StopFunctionStep(),
        pipelines.PrintkeyStep(key="local_label"),
    ]
    pipeline = Pipeline(steps, success_message="Function stoped successfully.")
    pipeline.run(
        {
            "project_path": Path.cwd(),
            "verbose": verbose,
            "root": stop_function.__name__,
        }
    )


def restart_function(
    verbose: bool,
):
    steps = [
        pipelines.ReadManifestStep(),
        pipelines.GetClientStep(),
        pipelines.GetContainerManagerStep(),
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
    verbose: bool,
):
    steps = [
        pipelines.ReadManifestStep(),
        pipelines.GetClientStep(),
        pipelines.GetContainerManagerStep(),
        pipelines.GetFunctionStatusStep(),
        pipelines.PrintColoredTableStep(key="status"),
    ]
    pipeline = Pipeline(steps)
    pipeline.run(
        {
            "verbose": verbose,
            "root": status_function.__name__,
            "project_path": Path.cwd(),
        }
    )


def logs_function(
    tail: str,
    follow: bool,
    profile: str,
    remote: bool,
    verbose: bool,
):
    if remote:
        steps = [
            pipelines.ReadManifestStep(),
            pipelines.GetProjectFilesStep(),
            pipelines.ValidateProjectStep(),
            pipelines.GetFunctionIdFromManifestStep(),
            pipelines.GetActiveConfigStep(),
            pipelines.BuildEndpointStep(FUNCTION_API_ROUTES["logs"]),
            pipelines.HttpGetRequestStep(),
            pipelines.CheckResponseStep("response"),
            pipelines.PrintColoredTableStep(key="results"),
        ]
        pipeline = Pipeline(steps)
        pipeline.run(
            {
                "project_path": Path.cwd(),
                "profile": profile,
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
            pipelines.ReadManifestStep(),
            pipelines.GetClientStep(),
            pipelines.GetContainerManagerStep(),
            pipelines.GetContainerKeyStep(),
            pipelines.GetFunctionLogsStep(tail=tail, follow=follow),
            pipelines.PrintkeyStep(key="logs"),
        ]
        pipeline = Pipeline(steps)
        pipeline.run(
            {
                "verbose": verbose,
                "root": logs_function.__name__,
                "project_path": Path.cwd(),
            }
        )


def push_function(
    confirm: bool,
    profile: str,
    verbose: bool,
):
    steps = [
        pipelines.GetActiveConfigStep(),
        pipelines.ReadManifestStep(),
        pipelines.GetProjectFilesStep(),
        pipelines.ValidateProjectStep(),
        pipelines.ValidateRemoteFunctionExistStep(),
        pipelines.BuildEndpointStep(FUNCTION_API_ROUTES["base"]),
        pipelines.CreateFunctionStep(),
        pipelines.SaveFunctionIDStep(),
        pipelines.ConfirmOverwritePushFunctionStep(),
        pipelines.BuildEndpointStep(FUNCTION_API_ROUTES["detail"]),
        pipelines.UpdateFunctionSettings(),
        pipelines.BuildEndpointStep(FUNCTION_API_ROUTES["zip_file"]),
        pipelines.CompressProjectStep(),
        pipelines.UploadFileStep(),
        pipelines.CheckResponseStep(response_key="response"),
    ]
    pipeline = Pipeline(steps, success_message="Function uploaded successfully.")
    pipeline.run(
        {
            "project_path": Path.cwd(),
            "profile": profile,
            "overwrite": {
                "confirm": confirm,
                "message": "Are you sure you want to overwrite the remote files?",
            },
            "validations": {
                "manifest_file": True,
                "function_exists": False,
            },
            "verbose": verbose,
            "root": push_function.__name__,
        }
    )


def pull_function(
    remote_id: str,
    profile: str,
    confirm: bool = False,
    verbose: bool = False,
):
    steps = [
        pipelines.GetActiveConfigStep(),
        pipelines.CheckRemoteIdRequirementStep(),  # New step to validate remote_id
        pipelines.GetRemoteFunctionDetailSteps(FUNCTION_API_ROUTES["detail"]),
        pipelines.CheckFunctionDetailResponse(),
        pipelines.ParseFunctionDetailsResponse(),
        pipelines.GetRemoteFunctionLocalMetadataStep(),
        pipelines.ValidateFunctionHasAlreadyBeenPulled(),
        pipelines.ConfirmOverwritePullFunctionStep(),
        pipelines.BuildEndpointStep(FUNCTION_API_ROUTES["zip_file"]),
        pipelines.DownloadFileStep(),
        pipelines.CheckResponseStep("function_zip_content"),
        pipelines.ExtractProjectStep(),
        pipelines.GetFunctionParametersStep(),
        pipelines.SaveManifestStep(),
        pipelines.ReadManifestStep(),
        pipelines.GetProjectFilesStep(),
        pipelines.ValidateProjectStep(),
        pipelines.PrintFunctionPath(),
    ]
    pipeline = Pipeline(steps)
    pipeline.run(
        {
            "project_path": Path.cwd(),
            "confirm": confirm,
            "profile": profile,
            "remote_id": remote_id,
            "verbose": verbose,
            "root": pull_function.__name__,
            "validations": {
                "manifest_file_exists": True,
                "function_exists": True,
            },
        }
    )


def clean_functions(
    confirm: bool,
    verbose: bool,
):
    steps = [
        pipelines.ReadManifestStep(),
        pipelines.ConfirmOverwriteStep(),
        pipelines.GetClientStep(),
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
            "project_path": Path.cwd(),
            "verbose": verbose,
            "root": clean_functions.__name__,
        }
    )


def add_function(
    profile: str,
    name: str,
    label: str,
    runtime: str,
    is_raw: bool,
    http_methods: list[str],
    http_has_cors: bool,
    scheduler_cron: str,
    timeout: int,
    environment: str,
):
    steps = [
        pipelines.GetActiveConfigStep(),
        pipelines.CreateFunctionRemoteServerStep(),
    ]
    pipeline = Pipeline(steps)
    pipeline.run(
        {
            "profile": profile,
            "name": name,
            "label": label,
            "runtime": runtime,
            "is_raw": is_raw,
            "http_methods": http_methods,
            "http_has_cors": http_has_cors,
            "scheduler_cron": scheduler_cron,
            "timeout": timeout,
            "environment": environment,
            "root": add_function.__name__,
        }
    )


def delete_function(
    function_key: str,
    profile: str,
    confirm: bool,
    verbose: bool,
):
    steps = [
        pipelines.GetActiveConfigStep(),
        pipelines.ConfirmOverwriteStep(),
        pipelines.DeleteFunctionStep(),
    ]
    pipeline = Pipeline(
        steps, success_message=f"Function {function_key} deleted successfully."
    )
    pipeline.run(
        {
            "overwrite": {
                "confirm": confirm,
                "message": "Are you sure you want to delete the function?",
            },
            "profile": profile,
            "function_key": function_key,
            "verbose": verbose,
            "root": delete_function.__name__,
        }
    )


def get_function(
    function_key: str,
    profile: str,
    verbose: bool,
    format: OutputFormatFieldsEnum,
    fields: str,
):
    steps = [
        pipelines.GetActiveConfigStep(),
        pipelines.GetFunctionFromRemoteServerStep(),
    ]
    pipeline = Pipeline(steps)
    pipeline.run(
        {
            "profile": profile,
            "function_key": function_key,
            "format": format,
            "fields": fields,
            "verbose": verbose,
            "root": get_function.__name__,
        }
    )


def list_functions(
    profile: str,
    fields: str,
    filter: str,
    sort_by: str,
    page_size: int,
    page: int,
    format: OutputFormatFieldsEnum,
):
    steps = [
        pipelines.GetActiveConfigStep(),
        pipelines.ListFunctionsFromRemoteServerStep(),
    ]
    pipeline = Pipeline(
        steps, success_message="Functions retrieved from remote server successfully."
    )
    pipeline.run(
        {
            "profile": profile,
            "format": format,
            "fields": fields,
            "filter": filter,
            "sort_by": sort_by,
            "page_size": page_size,
            "page": page,
            "root": list_functions.__name__,
        }
    )


def update_function(
    function_key: str,
    profile: str,
    name: str,
    label: str,
    http_methods: list[str] | None,
    http_has_cors: bool | None,
    scheduler_cron: str | None,
    runtime: str | None,
    is_raw: bool | None,
    timeout: int | None,
    environment: str | None,
):
    steps = [
        pipelines.GetActiveConfigStep(),
        pipelines.GetRemoteFunctionDetailSteps(FUNCTION_API_ROUTES["detail"]),
        pipelines.CheckFunctionDetailResponse(),
        pipelines.ParseFunctionDetailsResponse(),
        pipelines.UpdateFunctionStep(),
    ]
    pipeline = Pipeline(
        steps, success_message=f"Function {function_key} updated successfully."
    )
    pipeline.run(
        {
            "profile": profile,
            "remote_id": function_key,
            "update_data": {
                "name": name,
                "label": label,
                "serverless": {
                    "runtime": runtime,
                    "params": None,
                    "authToken": None,
                    "isRawFunction": is_raw,
                    "timeout": timeout,
                },
                "triggers": {
                    "httpMethods": http_methods,
                    "httpHasCors": http_has_cors,
                    "schedulerCron": scheduler_cron,
                    "schedulerEnabled": (
                        False
                        if scheduler_cron == ""
                        else (True if scheduler_cron is not None else None)
                    ),
                },
                "environment": environment,
            },
            "name": name,
            "label": label,
            "root": update_function.__name__,
        }
    )
