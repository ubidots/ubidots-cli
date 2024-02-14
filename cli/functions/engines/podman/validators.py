from podman import PodmanClient

from cli.functions.engines.validators import AbstractEngineValidator


class FunctionPodmanValidator(AbstractEngineValidator):
    def __init__(self, client: PodmanClient):
        super().__init__(client)
