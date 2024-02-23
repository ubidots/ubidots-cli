from functools import lru_cache

from pydantic_settings import BaseSettings

# class EngineSettings(BaseModel):


class EngineSettings(BaseSettings):
    HUB_USERNAME: str = "cristianrubioa"
    CONTAINER_PORT: str = "8080/tcp"
    CONTAINER_KEY: str = "ubidots_cli_container"
    CONTAINER_LABEL_PREFIX: str = "lambda_dev"
    HOST: str = "127.0.0.1"
    PORT: int = 9000
    VOLUME_PATH: str = "/var/task"
    VOLUME_MODE: str = "rw"
    VOLUME_MAPPING: dict = {"bind": VOLUME_PATH, "mode": VOLUME_MODE}
    IS_DETACH: bool = True
    RIE_INVOCATION_PATH: str = "/2015-03-31/functions/function/invocations"


@lru_cache
def get_settings():
    return EngineSettings()


engine_settings = get_settings()
