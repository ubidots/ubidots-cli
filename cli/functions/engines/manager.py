from dataclasses import dataclass

from docker import DockerClient
from docker.errors import DockerException

from cli.commons.utils import exit_with_error_message
from cli.functions.engines.docker.client import FunctionDockerClient
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.podman.client import FunctionPodmanClient


@dataclass
class FunctionEngineClientManager:
    engine: FunctionEngineTypeEnum

    def get_client(self) -> FunctionDockerClient | FunctionPodmanClient:
        if self.engine == FunctionEngineTypeEnum.DOCKER:
            try:
                docker_client = DockerClient()
            except (DockerException, PermissionError) as error:
                exit_with_error_message(exception=error)

            return FunctionDockerClient(client=docker_client, engine=self.engine)

        # if self.engine == FunctionEngineTypeEnum.PODMAN:
        #     podman_client = PodmanClient()
        #     return FunctionPodmanClient(client=podman_client)

        error_message = f"Unsupported engine type: {self.engine}"
        raise ValueError(error_message)
