from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from typing import Any
from typing import Protocol

from cli.functions.engines.abstracts.validators import AbstractEngineValidator


@dataclass
class AbstractImageDownloader(ABC):
    client: Any

    @abstractmethod
    def pull_image(self, image_name: str):
        raise NotImplementedError


class AbstractEngineClient(Protocol):
    @abstractmethod
    def get_validator(self) -> AbstractEngineValidator:
        raise NotImplementedError

    @abstractmethod
    def get_downloader(self) -> AbstractImageDownloader:
        raise NotImplementedError
