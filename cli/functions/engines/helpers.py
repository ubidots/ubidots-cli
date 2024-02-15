from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from typing import Any

from cli.functions.engines.exceptions import ImageFetchException
from cli.functions.engines.exceptions import ImageNotFoundException


@dataclass
class AbstractImageDownloader(ABC):
    client: Any

    @abstractmethod
    def pull_image(self, image_name: str):
        raise NotImplementedError

    @staticmethod
    def _image_not_found_on_hub(image_name: str) -> Exception:
        return ImageNotFoundException(image_name)

    @staticmethod
    def _image_fetch_error(image_name: str) -> Exception:
        return ImageFetchException(image_name)

    @staticmethod
    def raise_exception(error_type: str, image_name: str) -> None:
        error_map = {
            "image_not_found_on_hub": AbstractImageDownloader._image_not_found_on_hub,
            "image_fetch_error": AbstractImageDownloader._image_fetch_error,
        }

        error_function = error_map.get(error_type)
        if error_function:
            raise error_function(image_name)
        error_message = f"Unknown error type: {error_type}"
        raise ValueError(error_message)
