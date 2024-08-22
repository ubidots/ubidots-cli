from dataclasses import field

from docker import DockerClient
from docker.errors import APIError
from docker.errors import ImageNotFound

from cli.functions.engines.abstracts.validators import AbstractEngineValidator
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.exceptions import EngineNotInstalledException
from cli.functions.engines.exceptions import ImageNotAvailableLocallyException


class FunctionDockerValidator(AbstractEngineValidator):
    client: DockerClient = field(default_factory=DockerClient)
    engine: FunctionEngineTypeEnum = field(default=FunctionEngineTypeEnum.DOCKER)

    def validate_engine_installed(self):
        try:
            self.client.ping()
        except APIError as error:
            raise EngineNotInstalledException(engine=self.engine) from error

    def validate_image_available_locally(self, image_name):
        try:
            self.client.images.get(image_name)
        except ImageNotFound as error:
            raise ImageNotAvailableLocallyException(
                engine=self.engine, image_name=image_name
            ) from error
