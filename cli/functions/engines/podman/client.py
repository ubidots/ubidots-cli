from dataclasses import dataclass
from dataclasses import field

from podman import PodmanClient

from cli.functions.engines.abstracts.client import AbstractEngineClient
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.podman.container import \
    FunctionPodmanContainerManager
from cli.functions.engines.podman.image import FunctionPodmanImageDownloader
from cli.functions.engines.podman.validators import FunctionPodmanValidator


@dataclass
class FunctionPodmanClient(AbstractEngineClient):
    client: PodmanClient = field(default_factory=PodmanClient)
    engine: FunctionEngineTypeEnum = field(default=FunctionEngineTypeEnum.PODMAN)

    def get_validator(self) -> FunctionPodmanValidator:
        return FunctionPodmanValidator(client=self.client, engine=self.engine)

    def get_downloader(self) -> FunctionPodmanImageDownloader:
        return FunctionPodmanImageDownloader(client=self.client)

    def get_container_manager(self) -> FunctionPodmanContainerManager:
        return FunctionPodmanContainerManager(client=self.client, engine=self.engine)
