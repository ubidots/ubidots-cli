from dataclasses import dataclass
from dataclasses import field

from podman import PodmanClient

from cli.functions.engines.abstracts.clients import AbstractEngineClient
from cli.functions.engines.abstracts.clients import AbstractImageDownloader
from cli.functions.engines.podman.validators import FunctionPodmanValidator


@dataclass
class FunctionPodmanImageDownloader(AbstractImageDownloader):
    client: PodmanClient = field(default_factory=PodmanClient)


class FunctionPodmanClient(AbstractEngineClient):
    client: PodmanClient = field(default_factory=PodmanClient)

    def get_validator(self) -> FunctionPodmanValidator:
        return FunctionPodmanValidator(client=self)

    def get_downloader(self) -> FunctionPodmanImageDownloader:
        return FunctionPodmanImageDownloader(client=self)
