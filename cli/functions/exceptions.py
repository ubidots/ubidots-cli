class FolderAlreadyExistsError(Exception):
    def __init__(self, name: str):
        error_message = f"A folder named '{name}' already exists."
        super().__init__(error_message)


class TemplateNotFoundError(Exception):
    def __init__(self, language: str, template_file: str):
        error_message = f"Template for '{language}' not found at '{template_file}'."
        super().__init__(error_message)


class PermissionDeniedError(Exception):
    def __init__(self, error: str):
        error_message = f"Permission denied: {error}."
        super().__init__(error_message)
