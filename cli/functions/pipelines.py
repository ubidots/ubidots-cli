import zipfile
from io import BytesIO
from typing import Any

import httpx
import typer

from cli.commons.styles import print_colored_table
from cli.commons.utils import build_endpoint
from cli.commons.utils import check_response_status
from cli.commons.utils import exit_with_error_message
from cli.commons.utils import exit_with_success_message
from cli.functions.enums import FunctionProjectValidationTypeEnum
from cli.functions.helpers import compress_project_to_zip
from cli.functions.helpers import ensure_project_integrity


class Pipeline:
    def __init__(self, steps: list["PipelineStep"], success_message: str = ""):
        self.steps = steps
        self.success_message = success_message

    def _handle_success(self) -> None:
        if self.success_message:
            exit_with_success_message(self.success_message)

    def _handle_failure(self, step: "PipelineStep", exception: Exception) -> None:
        _ = step
        exit_with_error_message(exception=exception)

    def run(self, initial_data: dict[str, Any]) -> dict[str, Any]:
        data = initial_data
        for step in self.steps:
            try:
                data = step.execute(data)
            except Exception as error:
                self._handle_failure(step, error)
                break

        else:
            self._handle_success()
        return data


class PipelineStep:
    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        _ = data
        error_message = "Each step must implement the execute method."
        raise NotImplementedError(error_message)


class ValidateProjectStep(PipelineStep):
    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        project_path = data["project_path"]
        project_metadata = ensure_project_integrity(
            project_path=project_path,
            validation_flags={
                FunctionProjectValidationTypeEnum.MANIFEST_FILE: True,
                FunctionProjectValidationTypeEnum.MAIN_FILE_PRESENCE: True,
            },
        )
        data["project_metadata"] = project_metadata
        return data


class ConfirmOverwriteStep(PipelineStep):
    def __init__(self, confirm: bool, message: str):
        self.confirm = confirm
        self.message = message

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        project_metadata = data["project_metadata"]
        confirm = self.confirm or project_metadata.globals.auto_overwrite
        if not confirm and not typer.confirm(self.message):
            raise typer.Abort
        return data


class CompressProjectStep(PipelineStep):
    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        project_path = data["project_path"]
        zip_file = compress_project_to_zip(project_path)
        data["zip_file"] = zip_file
        return data


class ExtractProjectStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        response = data["response"]
        with zipfile.ZipFile(BytesIO(response.content), "r") as zip_ref:
            zip_ref.extractall(project_path)
        return data


class BuildEndpointStep(PipelineStep):
    def __init__(self, api_route: str):
        self.api_route = api_route

    def execute(self, data):
        project_metadata = data["project_metadata"]
        url, headers = build_endpoint(
            route=self.api_route,
            function_key=project_metadata.function.id,
        )
        data["url"] = url
        data["headers"] = headers
        return data


class UploadFileStep(PipelineStep):
    def execute(self, data):
        url = data["url"]
        headers = data["headers"]
        zip_file = data["zip_file"]
        project_metadata = data["project_metadata"]
        files = {
            "zipFile": (
                f"{project_metadata.project.name}.zip",
                zip_file,
                "application/zip",
            )
        }
        client = httpx.Client(follow_redirects=True)
        response = client.post(url=url, headers=headers, files=files)
        data["response"] = response
        return data


class HttpGetRequestStep(PipelineStep):
    def execute(self, data):
        url = data["url"]
        headers = data["headers"]
        response = httpx.get(url, headers=headers)
        data["response"] = response
        return data


class DownloadFileStep(HttpGetRequestStep): ...


class CheckResponseStep(PipelineStep):
    def execute(self, data):
        response = data["response"]
        check_response_status(response=response)
        return data


class PrintColoredTableStep(PipelineStep):
    def execute(self, data):
        response = data["response"]
        results = response.json()["results"]
        print_colored_table(results)
        return data
