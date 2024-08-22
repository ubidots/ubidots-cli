from dataclasses import dataclass
from dataclasses import field

from docker import DockerClient

from cli.functions.engines.abstracts.client import AbstractEngineClient
from cli.functions.engines.docker.container import \
    FunctionDockerContainerManager
from cli.functions.engines.docker.image import FunctionDockerImageDownloader
from cli.functions.engines.docker.network import FunctionDockerNetworkManager
from cli.functions.engines.docker.validators import FunctionDockerValidator
from cli.functions.engines.enums import FunctionEngineTypeEnum


@dataclass
class FunctionDockerClient(AbstractEngineClient):
    client: DockerClient = field(default_factory=DockerClient)
    engine: FunctionEngineTypeEnum = field(default=FunctionEngineTypeEnum.DOCKER)

    def get_validator(self) -> FunctionDockerValidator:
        return FunctionDockerValidator(client=self.client, engine=self.engine)

    def get_downloader(self) -> FunctionDockerImageDownloader:
        return FunctionDockerImageDownloader(client=self.client)

    def get_container_manager(self) -> FunctionDockerContainerManager:
        return FunctionDockerContainerManager(client=self.client, engine=self.engine)

    def get_network_manager(self) -> FunctionDockerNetworkManager:
        return FunctionDockerNetworkManager(client=self.client)
