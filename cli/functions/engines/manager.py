from dataclasses import dataclass

from docker import DockerClient
from podman import PodmanClient

from cli.functions.engines.docker.client import FunctionDockerClient
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.podman.client import FunctionPodmanClient


@dataclass
class FunctionEngineClientManager:
    engine_type: FunctionEngineTypeEnum

    def get_client(self) -> FunctionDockerClient | FunctionPodmanClient:
        if self.engine_type == FunctionEngineTypeEnum.DOCKER:
            docker_client = DockerClient()
            return FunctionDockerClient(client=docker_client)

        if self.engine_type == FunctionEngineTypeEnum.PODMAN:
            podman_client = PodmanClient()
            return FunctionPodmanClient(client=podman_client)

        error_message = f"Unsupported engine type: {self.engine_type}"
        raise ValueError(error_message)
