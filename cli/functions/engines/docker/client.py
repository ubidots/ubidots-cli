from dataclasses import dataclass
from dataclasses import field

from docker import DockerClient

from cli.functions.engines.abstracts.clients import AbstractEngineClient
from cli.functions.engines.docker.container import \
    FunctionDockerContainerManager
from cli.functions.engines.docker.image import FunctionDockerImageDownloader
from cli.functions.engines.docker.validators import FunctionDockerValidator


@dataclass
class FunctionDockerClient(AbstractEngineClient):
    client: DockerClient = field(default_factory=DockerClient)

    def get_validator(self) -> FunctionDockerValidator:
        return FunctionDockerValidator(client=self.client)

    def get_downloader(self) -> FunctionDockerImageDownloader:
        return FunctionDockerImageDownloader(client=self.client)

    def get_container(self) -> FunctionDockerContainerManager:
        return FunctionDockerContainerManager(client=self.client)
