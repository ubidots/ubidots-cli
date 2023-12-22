import os
import re
from pathlib import Path

from cli import settings
from cli.functions.models import FunctionProjectMetadata
from cli.functions.utils import read_manifest_project_file


class ProjectValidationDataManager:
    def __init__(self, project_path: Path):
        self.project_path: Path = project_path

    def prepare_data(self) -> tuple[FunctionProjectMetadata, list[Path]]:
        project_metadata = read_manifest_project_file(self.project_path)
        project_files = self.enumerate_project_files()
        return project_metadata, project_files

    def enumerate_project_files(self) -> list[Path]:
        return [
            Path(root) / file
            for root, _, files in os.walk(self.project_path)
            for file in files
        ]


class FunctionProjectValidator:
    def __init__(
        self, project_metadata: FunctionProjectMetadata, project_files: list[Path]
    ):
        self.project_metadata = project_metadata
        self.project_files = project_files

    def run_all_validations(self):
        self.validate_manifest_file()
        self.validate_main_file_presence()
        self.validate_file_names()
        self.validate_file_count()
        self.validate_individual_file_size()

    def validate_manifest_file(self):
        if self.project_metadata.function.id is None:
            error_message = "Function not yet registered or synchronized with the platform. Missing function key."
            raise ValueError(error_message)

    def validate_main_file_presence(self):
        main_file_name = self.project_metadata.project.language.main_file
        main_file_found = any(
            file_path.name == main_file_name for file_path in self.project_files
        )
        if not main_file_found:
            error_message = (
                f"Main file '{main_file_name}' not found in the project directory."
            )
            raise FileNotFoundError(error_message)

    def validate_file_names(self):
        def is_safe_file_name(file_name: str) -> bool:
            return re.match(r"[^/\\]*$", file_name) is not None

        for file_path in self.project_files:
            if not is_safe_file_name(file_path.name):
                error_message = f"Unsafe file name detected: '{file_path}'"
                raise ValueError(error_message)

    def validate_file_count(self):
        max_files_allowed = settings.UBIDOTS_FUNCTIONS_MAX_FILES_ALLOWED
        if (file_count := len(self.project_files)) > max_files_allowed:
            error_message = (
                f"The project contains '{file_count}' files, "
                f"which exceeds the maximum allowed limit of '{max_files_allowed}'."
            )
            raise ValueError(error_message)

    def validate_individual_file_size(self):
        max_individual_file_size = settings.UBIDOTS_FUNCTIONS_DEFAULT_MAX_FILE_SIZE
        for file_path in self.project_files:
            if os.path.getsize(file_path) > max_individual_file_size:
                error_message = (
                    f"The file '{file_path}' exceeds the maximum allowed size of "
                    f"'{max_individual_file_size / (1024 * 1024)}' MB."
                )
                raise ValueError(error_message)
