from abc import abstractmethod
from typing import Protocol

from cli.functions.engines.abstracts.container import AbstractContainerManager
from cli.functions.engines.abstracts.image import AbstractImageDownloader
from cli.functions.engines.abstracts.network import AbstractNetworkManager
from cli.functions.engines.abstracts.validators import AbstractEngineValidator


class AbstractEngineClient(Protocol):
    @abstractmethod
    def get_validator(self) -> AbstractEngineValidator: ...

    @abstractmethod
    def get_downloader(self) -> AbstractImageDownloader: ...

    @abstractmethod
    def get_container_manager(self) -> AbstractContainerManager: ...

    @abstractmethod
    def get_network_manager(self) -> AbstractNetworkManager: ...
