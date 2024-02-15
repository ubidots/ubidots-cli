class DockerContainerAlreadyRunningError(Exception):
    def __init__(
        self,
        message="Docker container is already running. Please check your Docker containers.",
    ):
        super().__init__(message)


class DockerHostPortError(Exception):
    def __init__(self, host_port, message=None):
        if message is None:
            message = (
                f"Try specifying a different host port using the '--host-port' option "
                f"or free up the port '{host_port}'."
            )
        super().__init__(message)


class DockerContainerExecutionError(Exception):
    def __init__(self, error_message, message=None):
        if message is None:
            message = f"Error executing the container: {error_message}"
        super().__init__(message)
