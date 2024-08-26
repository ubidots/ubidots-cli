from dataclasses import dataclass
from pathlib import Path

from cli.functions.enums import FunctionProjectValidationTypeEnum
from cli.functions.models import FunctionProjectMetadata


def validate_manifest_file(function_id: str):
    if not function_id:
        error_message = "Function not yet registered or synchronized with the platform. Missing function key."
        raise ValueError(error_message)


def validate_main_file_presence(
    project_path: Path, project_files: list[Path], main_file: str
):
    main_file_found = any(
        file_path.name == main_file and file_path.parent == project_path
        for file_path in project_files
    )
    if not main_file_found:
        error_message = f"Main file '{main_file}' not found in the project directory."
        raise FileNotFoundError(error_message)


@dataclass
class FunctionProjectValidator:
    project_metadata: FunctionProjectMetadata
    project_files: list[Path]
    project_path: Path | None = None
    validation_flags: dict[FunctionProjectValidationTypeEnum, bool] | None = None

    def run_validations(self):
        if self.validation_flags.get(
            FunctionProjectValidationTypeEnum.MANIFEST_FILE, False
        ):
            self.validate_manifest_file()
        if self.validation_flags.get(
            FunctionProjectValidationTypeEnum.MAIN_FILE_PRESENCE, False
        ):
            self.validate_main_file_presence()

    def validate_manifest_file(self):
        if self.project_metadata.function.id is None:
            error_message = "Function not yet registered or synchronized with the platform. Missing function key."
            raise ValueError(error_message)

    def validate_main_file_presence(self):
        if self.project_path is None:
            error_message = "The main file's project could not be determined."
            raise FileNotFoundError(error_message)

        main_file_name = self.project_metadata.project.language.main_file
        main_file_found = any(
            file_path.name == main_file_name and file_path.parent == self.project_path
            for file_path in self.project_files
        )
        if not main_file_found:
            error_message = (
                f"Main file '{main_file_name}' not found in the project directory."
            )
            raise FileNotFoundError(error_message)
