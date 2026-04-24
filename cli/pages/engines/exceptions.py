class ContainerNotFoundException(Exception):
    def __init__(self, container_name: str):
        self.container_name = container_name
        super().__init__(f"Container '{container_name}' not found")


class ContainerAlreadyRunningException(Exception):
    def __init__(self, container_name: str):
        self.container_name = container_name
        super().__init__(f"Container '{container_name}' is already running")


class ContainerExecutionException(Exception):
    def __init__(self, message: str = "Container execution failed"):
        super().__init__(message)


class NetworkNotFoundException(Exception):
    def __init__(self, network_id: str):
        self.network_id = network_id
        super().__init__(f"Network '{network_id}' not found")


class EngineNotInstalledException(Exception):
    def __init__(self, engine: str):
        message = (
            f"'{engine}' is not installed or not running. "
            f"Please ensure '{engine}' is properly installed and running."
        )
        super().__init__(message)


class ImageNotFoundException(Exception):
    def __init__(self, image_name: str):
        super().__init__(f"Image '{image_name}' does not exist on Hub.")


class ImageFetchException(Exception):
    def __init__(self, image_name: str):
        super().__init__(f"Failed to fetch image '{image_name}' from Hub.")
