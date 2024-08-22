from dataclasses import field

from podman import PodmanClient

from cli.functions.engines.abstracts.validators import AbstractEngineValidator
from cli.functions.engines.enums import FunctionEngineTypeEnum


class FunctionPodmanValidator(AbstractEngineValidator):
    client: PodmanClient = field(default_factory=PodmanClient)
    engine: FunctionEngineTypeEnum = field(default=FunctionEngineTypeEnum.PODMAN)

    def validate_engine_installed(self): ...

    def validate_image_available_locally(self, image_name: str): ...
