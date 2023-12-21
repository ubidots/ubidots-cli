import os
import re
from pathlib import Path

from cli import settings
from cli.functions.models import FunctionProjectMetadata


class FunctionProjectValidator:
    def __init__(self, project_path: Path, project_metadata: FunctionProjectMetadata):
        self.project_path = project_path
        self.project_metadata = project_metadata

    @staticmethod
    def _is_safe_file_name(file_name: str) -> bool:
        return re.match(r"[^/\\]*$", file_name) is not None

    def _enumerate_project_files(self):
        for root, dirs, files in os.walk(self.project_path):
            _ = dirs
            for file in files:
                yield Path(root) / file

    def run_all_validations(self):
        self.validate_manifest_file()
        self.validate_main_file_presence()
        self.validate_file_names()
        self.validate_file_count()
        self.validate_individual_file_size()

    def validate_manifest_file(self):
        if self.project_metadata.function is None:
            error_message = "Function not yet registered or synchronized with the platform. Missing function key."
            raise ValueError(error_message)

    def validate_main_file_presence(self):
        main_file_name = self.project_metadata.project.language.main_file
        main_file_path = self.project_path / main_file_name

        if not main_file_path.exists():
            error_message = (
                f"Main file '{main_file_name}' not found in the project directory."
            )
            raise FileNotFoundError(error_message)

    def validate_file_names(self):
        for file_path in self._enumerate_project_files():
            if not self._is_safe_file_name(file_path.name):
                error_message = f"Unsafe file name detected: '{file_path}'"
                raise ValueError(error_message)

    def validate_file_count(self):
        max_files_allowed = settings.UBIDOTS_FUNCTIONS_MAX_FILES_ALLOWED
        if (
            file_count := len(list(self._enumerate_project_files()))
        ) > max_files_allowed:
            error_message = (
                f"The project contains '{file_count}' files, "
                f"which exceeds the maximum allowed limit of '{max_files_allowed}'."
            )
            raise ValueError(error_message)

    def validate_individual_file_size(self):
        max_individual_file_size = settings.UBIDOTS_FUNCTIONS_DEFAULT_MAX_FILE_SIZE
        for file_path in self._enumerate_project_files():
            if os.path.getsize(file_path) > max_individual_file_size:
                error_message = (
                    f"The file '{file_path}' exceeds the maximum allowed size of "
                    f"'{max_individual_file_size / (1024 * 1024)}' MB."
                )
                raise ValueError(error_message)
