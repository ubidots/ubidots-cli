class DockerNotInstalledError(Exception):
    def __init__(
        self,
        message="Docker is not installed or not running. Please ensure Docker is properly installed and running.",
    ):
        super().__init__(message)


class DockerImageNotFoundError(Exception):
    def __init__(self, message="Docker image does not exist on Docker Hub."):
        super().__init__(message)


class DockerImageNotAvailableLocallyError(Exception):
    def __init__(
        self,
        message="Docker image is not available locally. Ensure Docker is installed and running.",
    ):
        super().__init__(message)
