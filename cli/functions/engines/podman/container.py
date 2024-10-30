from dataclasses import field

from podman import PodmanClient

from cli.functions.engines.abstracts.client import AbstractContainerManager
from cli.functions.engines.enums import FunctionEngineTypeEnum


class FunctionPodmanContainerManager(AbstractContainerManager):
    client: PodmanClient = field(default_factory=PodmanClient)
    engine: FunctionEngineTypeEnum = field(default=FunctionEngineTypeEnum.PODMAN)

    def status(self, *args, **kwargs): ...

    def get(self, *args, **kwargs): ...

    def list(self, *args, **kwargs): ...

    def logs(self, *args, **kwargs): ...

    def start(self, *args, **kwargs): ...

    def stop(self, *args, **kwargs): ...

    def restart(self, *args, **kwargs): ...
