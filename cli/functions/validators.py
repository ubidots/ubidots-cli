from pathlib import Path


def validate_function_exists(function_id: str):
    if not function_id:
        error_message = "Function not yet registered or synchronized with the platform. Missing function key."
        raise ValueError(error_message)


def validate_main_file_exists(
    project_path: Path, project_files: list[Path], main_file: str
):
    main_file_found = any(
        file_path.name == main_file and file_path.parent == project_path
        for file_path in project_files
    )
    if not main_file_found:
        error_message = f"Main file '{main_file}' not found in the project directory."
        raise FileNotFoundError(error_message)
