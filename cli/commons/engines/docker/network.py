from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass

from docker import DockerClient


@dataclass
class BaseDockerNetworkManager(ABC):
    client: DockerClient

    def get(self, network_id: str):
        """Get a network by ID or name."""
        return self.client.networks.get(network_id)

    def list(self, names: list[str] | None = None):
        """List networks by names."""
        return self.client.networks.list(names=names or [])

    @abstractmethod
    def create(self, *args, **kwargs): ...
