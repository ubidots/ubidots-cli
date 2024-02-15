from dataclasses import dataclass

from docker import DockerClient
from docker.errors import APIError
from docker.errors import ImageNotFound

from cli.functions.engines.enums import FunctionEngineServeEnum
from cli.functions.engines.validators import AbstractEngineValidator


@dataclass
class FunctionDockerValidator(AbstractEngineValidator):
    client: DockerClient

    def validate_engine_installed(self):
        try:
            self.client.ping()
        except APIError:
            self.raise_exception(
                "engine_not_installed", engine=FunctionEngineServeEnum.DOCKER.value
            )

    def validate_image_available_locally(self, image_name: str):
        try:
            self.client.images.get(image_name)
        except ImageNotFound:
            self.raise_exception(
                "image_not_available_locally",
                engine=FunctionEngineServeEnum.DOCKER.value,
                image_name=image_name,
            )
