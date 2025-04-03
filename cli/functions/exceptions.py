class FolderAlreadyExistsError(Exception):
    def __init__(self, name: str):
        error_message = f"A folder named '{name}' already exists."
        super().__init__(error_message)


class FunctionWithIdAlreadyExistsError(Exception):

    def __init__(
        self, id: str, function_path: str, alternative_command: str | None = None
    ):
        error_message = (
            f"A function with ID '{id}' has already been pulled at '{function_path}'"
            + (
                f" Run '{alternative_command}' in that directory to update it."
                if alternative_command
                else ""
            )
        )
        super().__init__(error_message)


class FunctionWithNameAlreadyExistsError(Exception):

    def __init__(self, name: str, function_path: str):
        error_message = (
            f"A function with name '{name}' already exists at '{function_path}'"
        )
        super().__init__(error_message)


class TemplateNotFoundError(Exception):
    def __init__(self, language: str, template_file: str):
        error_message = f"Template for '{language}' not found at '{template_file}'."
        super().__init__(error_message)


class PermissionDeniedError(Exception):
    def __init__(self, error: str):
        error_message = f"Permission denied: {error}."
        super().__init__(error_message)


class RemoteFunctionNotFoundError(Exception):
    def __init__(self, function_id: str):
        error_message = f"Function with id={function_id} not found."
        super().__init__(error_message)
