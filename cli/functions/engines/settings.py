from functools import lru_cache

from pydantic import BaseModel
from pydantic_settings import BaseSettings

from cli.functions.engines.enums import ContainerNetworkModeEnum
from cli.functions.engines.enums import FunctionEngineTypeEnum


class FunctionRIEContainerSettings(BaseModel):
    PREFIX_NAME: str = "frie"
    LABEL_KEY: str = "ubidots_cli_function"
    API_INVOKE_BASE_PATH: str = "/2015-03-31/functions/function/invocations"
    INTERNAL_PORT: str = "8080/tcp"
    EXTERNAL_PORT: int = 9000
    VOLUME_PATH: str = "/var/task"
    VOLUME_MODE: str = "rw"
    VOLUME_MAPPING: dict = {"bind": VOLUME_PATH, "mode": VOLUME_MODE}
    IS_RAW_LABEL_KEY: str = "is_raw"
    URL_LABEL_KEY: str = "target_url"


class ContainerSettings(BaseModel):
    FRIE: FunctionRIEContainerSettings = FunctionRIEContainerSettings()
    LABEL_PREFIX: str = "lambda_fn"
    DEFAULT_LABEL_LENGTH: int = 10
    IS_DETACH: bool = True
    NETWORK_NAME: str = "ubidots_cli_function_rie"
    NETWORK_DRIVER: ContainerNetworkModeEnum = ContainerNetworkModeEnum.BRIDGE
    DEFAULT_ENGINE: FunctionEngineTypeEnum = FunctionEngineTypeEnum.DOCKER


class EngineSettings(BaseSettings):
    CONTAINER: ContainerSettings = ContainerSettings()
    HUB_PREFFIX: str = "functions"
    DEFAULT_START_PORT_RANGE: int = 8040
    DEFAULT_END_PORT_RANGE: int = 65535


@lru_cache
def get_settings():
    return EngineSettings()


engine_settings = get_settings()
