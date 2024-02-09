import os
import re
from pathlib import Path

from docker import DockerClient
from docker import errors as docker_errors

from cli.functions.enums import FunctionProjectValidationTypeEnum
from cli.functions.exceptions import DockerImageNotAvailableLocallyError
from cli.functions.exceptions import DockerNotInstalledError
from cli.functions.models import FunctionProjectMetadata
from cli.settings import settings


class FunctionProjectValidator:
    def __init__(
        self,
        project_metadata: FunctionProjectMetadata,
        project_files: list[Path],
        project_path: Path | None = None,
        run_all_validations: bool = False,
        validation_flags: dict[FunctionProjectValidationTypeEnum, bool] | None = None,
    ):
        self.project_path = project_path
        self.project_metadata = project_metadata
        self.project_files = project_files
        self.run_all_validations = run_all_validations

        if validation_flags is None:
            validation_flags = {}
        self.validation_flags = validation_flags

    def run_validations(self):
        if self.run_all_validations or self.validation_flags.get(
            FunctionProjectValidationTypeEnum.MANIFEST_FILE, False
        ):
            self.validate_manifest_file()
        if self.run_all_validations or self.validation_flags.get(
            FunctionProjectValidationTypeEnum.MAIN_FILE_PRESENCE, False
        ):
            self.validate_main_file_presence()
        if self.run_all_validations or self.validation_flags.get(
            FunctionProjectValidationTypeEnum.FILE_NAMES, False
        ):
            self.validate_file_names()
        if self.run_all_validations or self.validation_flags.get(
            FunctionProjectValidationTypeEnum.FILE_COUNT, False
        ):
            self.validate_file_count()
        if self.run_all_validations or self.validation_flags.get(
            FunctionProjectValidationTypeEnum.INDIVIDUAL_FILE_SIZE, False
        ):
            self.validate_individual_file_size()

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

    def validate_file_names(self):
        def is_safe_file_name(file_name: str) -> bool:
            return re.match(r"[^/\\]*$", file_name) is not None

        for file_path in self.project_files:
            if not is_safe_file_name(file_path.name):
                error_message = f"Unsafe file name detected: '{file_path}'"
                raise ValueError(error_message)

    def validate_file_count(self):
        max_files_allowed = settings.FUNCTIONS.ZIP_FILE.MAX_FILES_ALLOWED
        if (file_count := len(self.project_files)) > max_files_allowed:
            error_message = (
                f"The project contains '{file_count}' files, "
                f"which exceeds the maximum allowed limit of '{max_files_allowed}'."
            )
            raise ValueError(error_message)

    def validate_individual_file_size(self):
        max_individual_file_size = settings.FUNCTIONS.ZIP_FILE.DEFAULT_MAX_FILE_SIZE
        for file_path in self.project_files:
            if os.path.getsize(file_path) > max_individual_file_size:
                error_message = (
                    f"The file '{file_path}' exceeds the maximum allowed size of "
                    f"'{max_individual_file_size / (1024 * 1024)}' MB."
                )
                raise ValueError(error_message)


class FunctionDockerValidator:
    def __init__(self, client: DockerClient, image_name: str):
        self.image_name = image_name
        self.client = client

    def validate_docker_is_installed(self):
        try:
            self.client.ping()
        except docker_errors.APIError as error:
            error_message = "Docker is not installed."
            raise DockerNotInstalledError(error_message) from error

    def validate_image_available_locally(self):
        try:
            self.client.images.get(self.image_name)
        except docker_errors.ImageNotFound as error:
            error_message = f"Image '{self.image_name}' is not available locally."
            raise DockerImageNotAvailableLocallyError(error_message) from error
