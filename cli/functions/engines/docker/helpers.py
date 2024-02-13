from docker.errors import APIError
from docker.errors import NotFound

from cli.functions.engines.helpers import AbstractImageDownloader


class DockerImageDownloader(AbstractImageDownloader):
    def pull_image(self, image_name: str):
        try:
            self.client.images.pull(image_name)
        except NotFound as error:
            self.handle_image_exception(error=error, image_name=image_name)
        except APIError as error:
            self.handle_server_exception(error=error, image_name=image_name)
