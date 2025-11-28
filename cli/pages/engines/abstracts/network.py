from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class AbstractNetworkManager(ABC):
    client: Any

    @abstractmethod
    def create(self, *args, **kwargs) -> Any:
        """Create a new network"""
        ...

    @abstractmethod
    def get(self, *args, **kwargs) -> Any:
        """Get a network by ID or name"""
        ...

    @abstractmethod
    def list(self, *args, **kwargs) -> Any:
        """List networks"""
        ...
