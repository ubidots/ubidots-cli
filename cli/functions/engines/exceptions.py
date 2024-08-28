import re

from cli.functions.engines.settings import engine_settings


class EngineException(Exception):
    """Base class for container engine-related errors."""


class ImageException(Exception):
    """Base class for container image-related errors."""


class ContainerException(Exception):
    """Base class for container container-related errors."""


class NetworkException(Exception):
    """Base class for container network-containers-related errors."""


class EngineNotInstalledException(EngineException):
    """Exception raised when the container engine is not installed or cannot be reached."""

    def __init__(self, engine: str):
        message = (
            f"'{engine}' is not installed or not running. "
            f"Please ensure '{engine}' is properly installed and running."
        )

        super().__init__(message)


class ImageNotAvailableLocallyException(ImageException):
    """Exception raised when a container image is not available locally."""

    def __init__(self, engine: str, image_name: str):
        message = f"Image '{image_name}' is not available locally. Ensure '{engine}' is installed and running."
        super().__init__(message)


class ImageNotFoundException(ImageException):
    def __init__(self, image_name: str):
        message = f"Image '{image_name}' does not exist on Hub."
        super().__init__(message)


class ImageFetchException(ImageException):
    def __init__(self, image_name: str):
        message = f"Failed to fetch image '{image_name}' from Hub."
        super().__init__(message)


class ContainerAlreadyRunningException(ContainerException):
    def __init__(self, container_name: str):
        message = f"Container '{container_name}' is already running."
        super().__init__(message)


class ContainerPortInUseException(ContainerException):
    def __init__(self, port: int):
        message = (
            f"The port {port} is already in use. "
            "Please consider using an alternative port."
        )
        super().__init__(message)


class ContainerExecutionException(ContainerException):
    def __init__(self):
        message = "Unexpected error executing the function."
        super().__init__(message)


class ContainerNotFoundException(ContainerException):
    def __init__(self, label: str):
        container_keys = [
            engine_settings.CONTAINER.FRIE.LABEL_KEY,
            engine_settings.CONTAINER.ARGO.LABEL_KEY,
        ]

        regex_pattern = "|".join(container_keys)
        if match := re.search(regex_pattern, label):
            extracted_label = label.split(match.group(0))[-1]
            label = extracted_label.strip("=_")

        message = f"Function with label '{label}' does not exist."
        super().__init__(message)


class NetworkNotFoundException(NetworkException):
    def __init__(self, network_id: str):
        message = f"Network with id '{network_id}' does not exist."
        super().__init__(message)
