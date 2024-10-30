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
    def status(self, *args, **kwargs) -> list[dict[str, Any]]: ...

    @abstractmethod
    def get(self, *args, **kwargs) -> Any: ...

    @abstractmethod
    def list(self, *args, **kwargs) -> list[Any]: ...

    @abstractmethod
    def logs(self, *args, **kwargs) -> Any: ...

    @abstractmethod
    def start(self, *args, **kwargs) -> Any: ...

    @abstractmethod
    def stop(self, *args, **kwargs) -> None: ...

    @abstractmethod
    def restart(self, *args, **kwargs) -> None: ...
