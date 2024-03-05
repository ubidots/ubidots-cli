from functools import lru_cache

from pydantic import BaseModel
from pydantic_settings import BaseSettings

from cli.functions.engines.enums import ContainerNetworkModeEnum


class ArgoContainerSettings(BaseModel):
    NAME: str = "argo"
    API_ADAPTER_BASE_PATH: str = "api/v2/adapter/"
    INTERNAL_ADAPTER_PORT: str = "8040/tcp"
    INTERNAL_TARGET_PORT: str = "8042/tcp"
    EXTERNAL_ADAPTER_PORT: int = 8040
    EXTERNAL_TARGET_PORT: int = 8042


class FunctionRIEContainerSettings(BaseModel):
    PREFIX_NAME: str = "frie"
    API_INVOKE_BASE_PATH: str = "/2015-03-31/functions/function/invocations"
    INTERNAL_PORT: str = "8080/tcp"
    EXTERNAL_PORT: int = 9000
    VOLUME_PATH: str = "/var/task"
    VOLUME_MODE: str = "rw"
    VOLUME_MAPPING: dict = {"bind": VOLUME_PATH, "mode": VOLUME_MODE}


class ContainerSettings(BaseModel):
    ARGO: ArgoContainerSettings = ArgoContainerSettings()
    FRIE: FunctionRIEContainerSettings = FunctionRIEContainerSettings()
    KEY: str = "ubidots_cli_container"
    LABEL_PREFIX: str = "lambda_dev"
    IS_DETACH: bool = True
    NETWORK_NAME: str = "ubidots_cli_function_rie"
    NETWORK_DRIVER: ContainerNetworkModeEnum = ContainerNetworkModeEnum.BRIDGE
    PORTS: list = [
        ARGO.INTERNAL_ADAPTER_PORT,
        ARGO.INTERNAL_TARGET_PORT,
        FRIE.INTERNAL_PORT,
    ]


class EngineSettings(BaseSettings):
    CONTAINER: ContainerSettings = ContainerSettings()
    HUB_USERNAME: str = "cristianrubioa"
    HOST: str = "127.0.0.1"
    DEFAULT_FROM_PORT: int = 8000
    DEFAULT_TO_PORT: int = 65535


@lru_cache
def get_settings():
    return EngineSettings()


engine_settings = get_settings()
