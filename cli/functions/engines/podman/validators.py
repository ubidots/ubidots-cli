from dataclasses import dataclass

from podman import PodmanClient

from cli.functions.engines.validators import AbstractEngineValidator


@dataclass
class FunctionPodmanValidator(AbstractEngineValidator):
    client: PodmanClient
