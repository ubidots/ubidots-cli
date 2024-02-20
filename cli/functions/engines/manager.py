from dataclasses import dataclass

from docker import DockerClient

from cli.functions.engines.docker.client import FunctionDockerClient
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.podman.client import FunctionPodmanClient


@dataclass
class FunctionEngineClientManager:
    engine: FunctionEngineTypeEnum

    def get_client(self) -> FunctionDockerClient | FunctionPodmanClient:
        if self.engine == FunctionEngineTypeEnum.DOCKER:
            docker_client = DockerClient()
            return FunctionDockerClient(client=docker_client, engine=self.engine)

        # if self.engine == FunctionEngineTypeEnum.PODMAN:
        #     podman_client = PodmanClient()
        #     return FunctionPodmanClient(client=podman_client)

        error_message = f"Unsupported engine type: {self.engine}"
        raise ValueError(error_message)
