from dataclasses import dataclass

from docker.errors import NotFound

from cli.commons.engines.docker.network import BaseDockerNetworkManager
from cli.pages.engines.enums import ContainerNetworkModeEnum
from cli.pages.engines.exceptions import NetworkNotFoundException
from cli.pages.engines.settings import page_engine_settings


@dataclass
class PageDockerNetworkManager(BaseDockerNetworkManager):

    def create(
        self,
        name: str = page_engine_settings.CONTAINER.NETWORK.NAME,
        driver: ContainerNetworkModeEnum = page_engine_settings.CONTAINER.NETWORK.DRIVER,
    ):
        return self.client.networks.create(name=name, driver=driver)

    def get(self, network_id: str):
        try:
            return self.client.networks.get(network_id)
        except NotFound as error:
            raise NetworkNotFoundException(network_id) from error

    def list(self, names: list[str] | None = None):
        names = names or [page_engine_settings.CONTAINER.NETWORK.NAME]
        return self.client.networks.list(names=names)
