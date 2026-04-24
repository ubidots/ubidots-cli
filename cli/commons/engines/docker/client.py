from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass

from docker import DockerClient


@dataclass
class BaseDockerClient(ABC):
    client: DockerClient

    @abstractmethod
    def get_container_manager(self): ...

    @abstractmethod
    def get_network_manager(self): ...

    @abstractmethod
    def get_downloader(self): ...

    @abstractmethod
    def get_validator(self): ...
