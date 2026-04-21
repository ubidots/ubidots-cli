from pydantic_settings import BaseSettings

from cli.pages.engines.enums import ContainerNetworkModeEnum
from cli.pages.engines.enums import PageEngineTypeEnum


class NetworkSettings:
    NAME: str = "ubidots_cli_pages"
    DRIVER: ContainerNetworkModeEnum = ContainerNetworkModeEnum.BRIDGE


class ContainerSettings:
    NETWORK: NetworkSettings = NetworkSettings()
    DEFAULT_ENGINE: PageEngineTypeEnum = PageEngineTypeEnum.DOCKER


class PageEngineSettings(BaseSettings):
    CONTAINER: ContainerSettings = ContainerSettings()


page_engine_settings = PageEngineSettings()
