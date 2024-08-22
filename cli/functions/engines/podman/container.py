from dataclasses import field

from podman import PodmanClient

from cli.functions.engines.abstracts.client import AbstractContainerManager
from cli.functions.engines.enums import FunctionEngineTypeEnum


class FunctionPodmanContainerManager(AbstractContainerManager):
    client: PodmanClient = field(default_factory=PodmanClient)
    engine: FunctionEngineTypeEnum = field(default=FunctionEngineTypeEnum.PODMAN)

    def status(self): ...

    def get(self): ...

    def list(self): ...

    def logs(self): ...

    def start(self): ...

    def stop(self): ...
