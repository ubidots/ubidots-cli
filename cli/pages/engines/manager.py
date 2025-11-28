from dataclasses import dataclass

from docker import DockerClient
from docker.errors import DockerException

from cli.commons.utils import exit_with_error_message
from cli.pages.engines.docker.client import PageDockerClient
from cli.pages.engines.enums import PageEngineTypeEnum


@dataclass
class PageEngineClientManager:
    """Factory for creating engine-specific clients (Docker/Podman)"""

    engine: PageEngineTypeEnum

    def get_client(self) -> PageDockerClient:
        if self.engine == PageEngineTypeEnum.DOCKER:
            try:
                docker_client = DockerClient()
            except (DockerException, PermissionError) as error:
                exit_with_error_message(exception=error)

            return PageDockerClient(client=docker_client, engine=self.engine)

        # Future: Podman support
        # if self.engine == PageEngineTypeEnum.PODMAN:
        #     podman_client = PodmanClient()
        #     return PagePodmanClient(client=podman_client)

        error_message = f"Unsupported engine type: {self.engine}"
        raise ValueError(error_message)
