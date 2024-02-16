from dataclasses import dataclass
from dataclasses import field

from podman import PodmanClient

from cli.functions.engines.abstracts.validators import AbstractEngineValidator


@dataclass
class FunctionPodmanValidator(AbstractEngineValidator):
    client: PodmanClient = field(default_factory=PodmanClient)
