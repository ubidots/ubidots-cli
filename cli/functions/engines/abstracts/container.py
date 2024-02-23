from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any


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
