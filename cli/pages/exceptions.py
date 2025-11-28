from pathlib import Path


class CurrentPlanDoesNotIncludePagesFeature(Exception):
    def __str__(self):
        return (
            "The current plan does not include the 'pages' feature. "
            "Please upgrade your plan to use this feature."
        )


class PageAlreadyExistsInCurrentDirectoryError(Exception):
    def __str__(self):
        return "A page already exists in the current directory. Please navigate to a different directory to create a new page."


class PageWithNameAlreadyExistsError(Exception):
    def __init__(self, name: str, page_path: str):
        error_message = f"A page with name '{name}' already exists at '{page_path}'"
        super().__init__(error_message)


class TemplateNotFoundError(Exception):
    def __init__(self, template_file: Path, page_type: str):
        self.template_file = template_file
        self.page_type = page_type

    def __str__(self):
        return f"Template for page type '{self.page_type}' not found at '{self.template_file}'"


class PageIsAlreadyRunningError(Exception):
    def __init__(self, name: str, url: str = ""):
        self.name = name
        self.url = url
        super().__init__(f"Page '{name}' is already running.")

    def __str__(self):
        message = f"Page '{self.name}' is already running."
        if self.url:
            message += f"\n\n🌐 Page URL: {self.url}"
        return message


class PageIsAlreadyStoppedError(Exception):
    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Page '{name}' is already stopped.")

    def __str__(self):
        return f"Page '{self.name}' is already stopped."
