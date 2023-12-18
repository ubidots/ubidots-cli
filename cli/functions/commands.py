import zipfile
from io import BytesIO
from pathlib import Path

import requests
import typer

from cli import settings
from cli.commons.utils import build_endpoint
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.utils import (compress_project_to_zip,
                                 read_manifest_project_file,
                                 save_manifest_project_file)
from cli.functions.validators import FunctionProjectValidator

app = typer.Typer(help="Tool for managing and deploying functions via API.")


@app.command(help="Create a new local function.")
def new(
    name: str = typer.Argument(
        default=settings.UBIDOTS_FUNCTIONS_DEFAULT_PROJECT_NAME,
        help="The name of the project folder.",
    )
):
    try:
        project_path = Path.cwd() / name if not Path(name).is_absolute() else Path(name)
        if project_path.exists():
            typer.echo(f"A folder named '{name}' already exists.")
            raise typer.Exit(1)

        language = FunctionLanguageEnum.choose(message="Select a programming language:")
        language_str = language.value

        template_file = (
            settings.UBIDOTS_FUNCTIONS_TEMPLATES_PATH / f"{language_str}.zip"
        )
        if not template_file.exists():
            typer.echo(f"Template for '{language_str}' not found at '{template_file}'.")
            raise typer.Exit(1)

        project_path.mkdir(parents=True, exist_ok=False)
        with zipfile.ZipFile(template_file, "r") as zip_ref:
            zip_ref.extractall(project_path)
        save_manifest_project_file(project_path=project_path, language=language)
        typer.echo(f"Project {language_str} created in '{project_path}'.")

    except PermissionError as error:
        typer.echo(f"Permission denied: {error}.")
        raise typer.Exit(1) from error


@app.command(
    help="Update and synchronize your local function code with the remote server."
)
def push():
    actual_path = Path.cwd()
    try:
        manifest_data = read_manifest_project_file(project_path=actual_path)
        validator = FunctionProjectValidator(
            project_path=actual_path, project_metadata=manifest_data
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
        function_key=manifest_data.function.id,
    )
    files = {
        "zipFile": (
            f"{manifest_data.project.name}.zip",
            zip_file_obj,
            "application/zip",
        )
    }
    try:
        response = requests.post(url, headers=headers, files=files)
        response.raise_for_status()
        typer.echo("Function uploaded successfully.")
    except requests.RequestException as error:
        error_message = f"Error uploading function: {error}"
        response_json = response.json()
        if "detail" in response_json:
            error_message += f"\nServer response: {response_json['detail']}"
        typer.echo(error_message)
        raise typer.Exit(1) from error


@app.command(
    help="Retrieve and update your local function code with the latest changes from the remote server."
)
def pull():
    actual_path = Path.cwd()
    try:
        manifest_data = read_manifest_project_file(project_path=actual_path)
        validator = FunctionProjectValidator(
            project_path=actual_path, project_metadata=manifest_data
        )
        validator.validate_manifest_file()

    except (FileNotFoundError, ValueError) as error:
        typer.echo(error)
        raise typer.Exit(1) from error

    url, headers = build_endpoint(
        route="/api/-/functions/{function_key}/zip-file/",
        function_key=manifest_data.function.id,
    )
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        typer.echo("Function downloaded successfully.")
    except requests.RequestException as error:
        error_message = f"Error downloading function: {error}"
        response_json = response.json()
        if "detail" in response_json:
            error_message += f"\nServer response: {response_json['detail']}"
        typer.echo(error_message)
        raise typer.Exit(1) from error

    with zipfile.ZipFile(BytesIO(response.content), "r") as zip_ref:
        zip_ref.extractall(actual_path)

    typer.echo("Function downloaded and unpacked successfully.")
