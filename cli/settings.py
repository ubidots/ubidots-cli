from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings


class ConfigSettings(BaseModel):
    API_DOMAIN: str = "https://industrial.api.ubidots.com"
    DIRECTORY_PATH: Path = Path.home() / ".ubidots_cli"
    FILE_PATH: Path = DIRECTORY_PATH / "config.yaml"


class FunctionSettings(BaseModel):
    class ZipFileSettings(BaseModel):
        MAX_FILES_ALLOWED: int = 2000
        DEFAULT_MAX_FILE_SIZE: int = 5 * 1024 * 1024  # 5MB

    class DockerSettings(BaseModel):
        HUB_USERNAME: str = "cristianrubioa"
        CONTAINER_PORT: int = 8080
        CONTAINER_LABEL: str = "ubidots_cli_container"
        HOST: str = "localhost"
        PORT: int = 9000
        VOLUME_PATH: str = "/var/task"
        VOLUME_MODE: str = "rw"
        VOLUME_MAPPING: dict = {"bind": VOLUME_PATH, "mode": VOLUME_MODE}
        IS_DETACH: bool = True
        RIE_INVOCATION_PATH: str = "/2015-03-31/functions/function/invocations"

    DEFAULT_PROJECT_NAME: str = "my_function"
    DEFAULT_MAIN_FILE_NAME: str = "main"
    PROJECT_METADATA_FILE: str = "manifest.yaml"
    TEMPLATES_PATH: Path = (
        Path(__file__).resolve().parent.parent / "cli" / "functions" / "templates"
    )
    DOCKER_CONFIG: DockerSettings = DockerSettings()
    ZIP_FILE: ZipFileSettings = ZipFileSettings()


class Settings(BaseSettings):
    CONFIG: ConfigSettings = ConfigSettings()
    FUNCTIONS: FunctionSettings = FunctionSettings()


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
