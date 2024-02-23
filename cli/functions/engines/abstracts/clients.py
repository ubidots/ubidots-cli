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
    def status(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def get(self) -> Any: ...

    @abstractmethod
    def list(self) -> list[Any]: ...

    @abstractmethod
    def logs(self) -> Any: ...

    @abstractmethod
    def start(self) -> Any: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def reload(self) -> None: ...


class AbstractEngineClient(Protocol):
    @abstractmethod
    def get_validator(self) -> AbstractEngineValidator: ...

    @abstractmethod
    def get_downloader(self) -> AbstractImageDownloader: ...

    @abstractmethod
    def get_container_manager(self) -> AbstractContainerManager: ...
