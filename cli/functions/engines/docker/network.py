from docker.errors import NotFound

from cli.commons.engines.docker.network import BaseDockerNetworkManager
from cli.functions.engines.enums import ContainerNetworkModeEnum
from cli.functions.engines.exceptions import NetworkNotFoundException
from cli.functions.engines.settings import engine_settings


class FunctionDockerNetworkManager(BaseDockerNetworkManager):

    def create(
        self,
        name: str = engine_settings.CONTAINER.NETWORK_NAME,
        driver: ContainerNetworkModeEnum = engine_settings.CONTAINER.NETWORK_DRIVER,
    ):
        return self.client.networks.create(name=name, driver=driver)

    def get(self, network_id: str):
        try:
            return self.client.networks.get(network_id)
        except NotFound as error:
            raise NetworkNotFoundException(network_id) from error

    def list(self, names: list[str] | None = None):
        if names is None:
            names = [engine_settings.CONTAINER.NETWORK_NAME]
        return self.client.networks.list(names=names)
