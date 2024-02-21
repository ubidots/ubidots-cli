from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any
from typing import Protocol

from cli.functions.engines.abstracts.validators import AbstractEngineValidator


@dataclass
class AbstractImageDownloader(ABC):
    client: Any

    @abstractmethod
    def pull_image(self, image_name: str): ...


@dataclass
class AbstractContainerManager(ABC):
    client: Any
    engine: Enum

    @abstractmethod
    def list(self) -> list[Any]: ...

    @abstractmethod
    def run(self) -> Any: ...

    @abstractmethod
    def status(self) -> Any: ...


class AbstractEngineClient(Protocol):
    @abstractmethod
    def get_validator(self) -> AbstractEngineValidator: ...

    @abstractmethod
    def get_downloader(self) -> AbstractImageDownloader: ...

    @abstractmethod
    def get_container_manager(self) -> AbstractContainerManager: ...
