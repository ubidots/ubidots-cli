from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class AbstractNetworkManager(ABC):
    client: Any

    @abstractmethod
    def create(self) -> Any: ...

    @abstractmethod
    def get(self) -> Any: ...

    @abstractmethod
    def list(self) -> Any: ...
