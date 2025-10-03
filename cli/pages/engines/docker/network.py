from dataclasses import field

from docker import DockerClient
from docker.errors import NotFound

from cli.pages.engines.abstracts.network import AbstractNetworkManager
from cli.pages.engines.enums import ContainerNetworkModeEnum
from cli.pages.engines.exceptions import NetworkNotFoundException
from cli.pages.engines.settings import page_engine_settings


class PageDockerNetworkManager(AbstractNetworkManager):
    client: DockerClient = field(default_factory=DockerClient)

    def create(
        self,
        name: str = page_engine_settings.CONTAINER.NETWORK_NAME,
        driver: ContainerNetworkModeEnum = page_engine_settings.CONTAINER.NETWORK_DRIVER,
    ):
        """Create a new network"""
        return self.client.networks.create(name=name, driver=driver)

    def get(self, network_id: str):
        """Get network by ID or name"""
        try:
            return self.client.networks.get(network_id)
        except NotFound as error:
            raise NetworkNotFoundException(network_id) from error

    def list(self, names: list[str] = None):
        """List networks by names"""
        names = names or [page_engine_settings.CONTAINER.NETWORK_NAME]
        return self.client.networks.list(names=names)
