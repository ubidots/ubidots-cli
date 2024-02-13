from docker import DockerClient
from docker.errors import APIError
from docker.errors import ImageNotFound

from cli.functions.engines.enums import FunctionEngineServeEnum
from cli.functions.engines.validators import AbstractEngineValidator


class FunctionDockerValidator(AbstractEngineValidator):
    def __init__(self, client: DockerClient):
        super().__init__(client)

    def validate_engine_installed(self):
        try:
            self.client.ping()
        except APIError as error:
            self.handle_engine_exception(
                error=error,
                engine=FunctionEngineServeEnum.DOCKER.value,
            )

    def validate_image_available_locally(self, image_name: str):
        try:
            self.client.images.get(image_name)
        except ImageNotFound as error:
            self.handle_image_exception(
                error=error,
                engine=FunctionEngineServeEnum.DOCKER.value,
                image_name=image_name,
            )
