from dataclasses import field

from docker import DockerClient
from docker.errors import APIError
from docker.errors import NotFound

from cli.functions.engines.abstracts.client import AbstractImageDownloader
from cli.functions.engines.exceptions import ImageFetchException
from cli.functions.engines.exceptions import ImageNotFoundException


class FunctionDockerImageDownloader(AbstractImageDownloader):
    client: DockerClient = field(default_factory=DockerClient)

    def pull_image(self, image_name):
        try:
            self.client.images.pull(image_name)
        except NotFound as error:
            raise ImageNotFoundException(image_name=image_name) from error
        except APIError as error:
            raise ImageFetchException(image_name=image_name) from error
