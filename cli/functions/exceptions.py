from enum import Enum


class FolderAlreadyExistsException(Exception):
    def __init__(self, name: str):
        error_message = f"A folder named '{name}' already exists."
        super().__init__(error_message)


class TemplateNotFoundException(Exception):
    def __init__(self, language: str, template_file: str):
        error_message = f"Template for '{language}' not found at '{template_file}'."
        super().__init__(error_message)


class PermissionDeniedException(Exception):
    def __init__(self, error: str):
        error_message = f"Permission denied: {error}."
        super().__init__(error_message)


class InvalidOptionException(Exception):
    def __init__(
        self,
        invalid_option: str,
        valid_options: list | type[Enum],
        context: str = "option",
    ):
        if isinstance(valid_options, type) and issubclass(valid_options, Enum):
            valid_options = [method.name for method in valid_options]

        valid_options_str = ", ".join(valid_options)
        error_message = (
            f"'{invalid_option}' is not a valid {context}. "
            f"Valid options are: {valid_options_str}."
        )
        super().__init__(error_message)
