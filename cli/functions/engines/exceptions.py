class EngineException(Exception):
    """Base class for container engine-related errors."""


class EngineNotInstalledException(EngineException):
    """Exception raised when the container engine is not installed or cannot be reached."""

    def __init__(self, engine: str):
        message = (
            f"'{engine}' is not installed or not running. "
            f"Please ensure '{engine}' is properly installed and running."
        )

        super().__init__(message)


class ImageNotAvailableLocallyException(EngineException):
    """Exception raised when a container image is not available locally."""

    def __init__(self, engine: str, image_name: str):
        message = f"Image '{image_name}' is not available locally. Ensure '{engine}' is installed and running."
        super().__init__(message)


class ImageNotFoundException(EngineException):
    def __init__(self, image_name: str):
        message = f"Image '{image_name}' does not exist on Hub."
        super().__init__(message)


class ImageFetchException(EngineException):
    def __init__(self, image_name: str):
        message = f"Failed to fetch image '{image_name}' from Hub."
        super().__init__(message)


class ContainerAlreadyRunningException(EngineException):
    def __init__(self, host: str, port: int):
        message = (
            f"Function is already running. Try specifying a different (host:port)=({host}:{port}) to bind "
            f"or free up the port '{port}'."
        )
        super().__init__(message)


class ContainerExecutionException(EngineException):
    def __init__(self):
        message = "Unexpected error executing the function."
        super().__init__(message)


class ContainerNotFoundException(EngineException):
    def __init__(self, label: str):
        message = f"Function with label '{label}' does not exist."
        super().__init__(message)
