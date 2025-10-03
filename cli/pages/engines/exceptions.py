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
