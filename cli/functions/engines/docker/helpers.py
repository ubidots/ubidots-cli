from docker.errors import APIError
from docker.errors import NotFound

from cli.functions.engines.helpers import AbstractImageDownloader


class DockerImageDownloader(AbstractImageDownloader):
    def pull_image(self, image_name: str):
        try:
            self.client.images.pull(image_name)
        except NotFound:
            self.raise_exception("image_not_found_on_hub", image_name=image_name)
        except APIError:
            self.raise_exception("image_fetch_error", image_name=image_name)
