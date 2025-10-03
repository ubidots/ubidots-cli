from dataclasses import dataclass
from dataclasses import field

from docker import DockerClient

from cli.pages.engines.abstracts.client import AbstractEngineClient
from cli.pages.engines.docker.container import PageDockerContainerManager
from cli.pages.engines.docker.network import PageDockerNetworkManager
from cli.pages.engines.enums import PageEngineTypeEnum


@dataclass
class PageDockerClient(AbstractEngineClient):
    client: DockerClient = field(default_factory=DockerClient)
    engine: PageEngineTypeEnum = field(default=PageEngineTypeEnum.DOCKER)

    def get_container_manager(self) -> PageDockerContainerManager:
        return PageDockerContainerManager(client=self.client, engine=self.engine)

    def get_network_manager(self) -> PageDockerNetworkManager:
        return PageDockerNetworkManager(client=self.client)
