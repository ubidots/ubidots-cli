from dataclasses import field

from podman import PodmanClient
from podman.errors import APIError
from podman.errors import ImageNotFound

from cli.functions.engines.abstracts.validators import AbstractEngineValidator
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.exceptions import EngineNotInstalledException
from cli.functions.engines.exceptions import ImageNotAvailableLocallyException


class FunctionPodmanValidator(AbstractEngineValidator):
    client: PodmanClient = field(default_factory=PodmanClient)

    def validate_engine_installed(self):
        try:
            self.client.info()
        except APIError as error:
            raise EngineNotInstalledException(
                engine=FunctionEngineTypeEnum.PODMAN.value
            ) from error

    def validate_image_available_locally(self, image_name: str):
        try:
            self.client.images.get(image_name)
        except ImageNotFound as error:
            raise ImageNotAvailableLocallyException(
                engine=FunctionEngineTypeEnum.PODMAN.value, image_name=image_name
            ) from error
