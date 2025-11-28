from abc import abstractmethod
from typing import Protocol

from cli.pages.engines.abstracts.container import AbstractContainerManager
from cli.pages.engines.abstracts.network import AbstractNetworkManager


class AbstractEngineClient(Protocol):
    @abstractmethod
    def get_container_manager(self) -> AbstractContainerManager:
        """Get container manager for this engine"""
        ...

    @abstractmethod
    def get_network_manager(self) -> AbstractNetworkManager:
        """Get network manager for this engine"""
        ...
