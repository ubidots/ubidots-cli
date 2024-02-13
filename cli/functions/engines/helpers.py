from abc import ABC
from abc import abstractmethod
from typing import Any

from cli.functions.engines.exceptions import ImageFetchException
from cli.functions.engines.exceptions import ImageNotFoundException


class AbstractImageDownloader(ABC):
    def __init__(self, client: Any):
        self.client = client

    @abstractmethod
    def pull_image(self, image_name: str):
        raise NotImplementedError

    def handle_image_exception(self, error: Exception, image_name: str) -> None:
        raise ImageNotFoundException(image_name) from error

    def handle_server_exception(self, error: Exception, image_name: str) -> None:
        raise ImageFetchException(image_name) from error
