from dataclasses import dataclass
from dataclasses import field

from docker import DockerClient
from docker.errors import APIError
from docker.errors import NotFound

from cli.functions.engines.abstracts.clients import AbstractEngineClient
from cli.functions.engines.abstracts.clients import AbstractImageDownloader
from cli.functions.engines.docker.validators import FunctionDockerValidator
from cli.functions.engines.exceptions import ImageFetchException
from cli.functions.engines.exceptions import ImageNotFoundException


@dataclass
class FunctionDockerImageDownloader(AbstractImageDownloader):
    client: DockerClient = field(default_factory=DockerClient)

    def pull_image(self, image_name: str):
        try:
            self.client.images.pull(image_name)
        except NotFound as error:
            raise ImageNotFoundException(image_name=image_name) from error
        except APIError as error:
            raise ImageFetchException(image_name=image_name) from error


@dataclass
class FunctionDockerClient(AbstractEngineClient):
    client: DockerClient = field(default_factory=DockerClient)

    def get_validator(self) -> FunctionDockerValidator:
        return FunctionDockerValidator(client=self.client)

    def get_downloader(self) -> FunctionDockerImageDownloader:
        return FunctionDockerImageDownloader(client=self.client)
