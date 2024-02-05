import zipfile
from io import BytesIO
from pathlib import Path

import typer

from cli.commons.enums import HTTPMethodEnum
from cli.commons.utils import build_endpoint
from cli.commons.utils import perform_http_request
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.enums import FunctionNodejsRuntimeLayerTypeEnum
from cli.functions.enums import FunctionPythonRuntimeLayerTypeEnum
from cli.functions.helpers import compress_project_to_zip
from cli.functions.helpers import save_manifest_project_file
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
