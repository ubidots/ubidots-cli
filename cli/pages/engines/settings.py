from functools import lru_cache

from pydantic import BaseModel
from pydantic_settings import BaseSettings

from cli.pages.engines.enums import ContainerNetworkModeEnum
from cli.pages.engines.enums import PageEngineTypeEnum


class FlaskManagerContainerSettings(BaseModel):
    NAME: str = "flask-pages-manager"
    LABEL_KEY: str = "ubidots_cli_pages_manager"
    HOSTNAME: str = "flask-manager"
    INTERNAL_PORT: str = "8044/tcp"
    EXTERNAL_PORT: int = 8044


class PageContainerSettings(BaseModel):
    PREFIX_NAME: str = "page"
    LABEL_KEY: str = "ubidots_cli_page"
    SUBDOMAIN_LABEL_KEY: str = "page_subdomain"
    UPSTREAM_LABEL_KEY: str = "page_upstream"
    PATH_LABEL_KEY: str = "page_path"
    INTERNAL_PORT: int = 5000
    VOLUME_PATH: str = "/app/page"
    VOLUME_MODE: str = "ro"
    VOLUME_MAPPING: dict = {"bind": VOLUME_PATH, "mode": VOLUME_MODE}


class ContainerSettings(BaseModel):
    FLASK_MANAGER: FlaskManagerContainerSettings = FlaskManagerContainerSettings()
    PAGE: PageContainerSettings = PageContainerSettings()
    IS_DETACH: bool = True
    NETWORK_NAME: str = "ubidots_cli_pages"
    NETWORK_DRIVER: ContainerNetworkModeEnum = ContainerNetworkModeEnum.BRIDGE
    DEFAULT_ENGINE: PageEngineTypeEnum = PageEngineTypeEnum.DOCKER


class PageEngineSettings(BaseSettings):
    CONTAINER: ContainerSettings = ContainerSettings()
    PYTHON_IMAGE: str = "ubidots/pages-server:latest"
    # Fallback if custom image unavailable
    FALLBACK_PYTHON_IMAGE: str = "python:3.12-slim"
    HOST_BIND: str = "127.0.0.1"


@lru_cache
def get_settings():
    return PageEngineSettings()


page_engine_settings = get_settings()
