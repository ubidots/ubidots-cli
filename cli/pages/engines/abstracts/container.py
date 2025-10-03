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
    def get(self, *args, **kwargs) -> Any:
        """Get a container by name or ID"""
        ...

    @abstractmethod
    def list(self, *args, **kwargs) -> list[Any]:
        """List containers with optional filters"""
        ...

    @abstractmethod
    def start(self, *args, **kwargs) -> Any:
        """Start a new container"""
        ...

    @abstractmethod
    def stop(self, *args, **kwargs) -> None:
        """Stop and remove a container"""
        ...

    @abstractmethod
    def logs(self, *args, **kwargs) -> Any:
        """Get container logs"""
        ...

    @abstractmethod
    def restart(self, *args, **kwargs) -> None:
        """Restart a container"""
        ...
