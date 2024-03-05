from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings


class ConfigSettings(BaseModel):
    API_DOMAIN: str = "https://industrial.api.ubidots.com"
    DIRECTORY_PATH: Path = Path.home() / ".ubidots_cli"
    FILE_PATH: Path = DIRECTORY_PATH / "config.yaml"


class RequestSettings(BaseModel):
    RETRY_MAX_ATTEMPTS: int = 5
    RETRY_DELAY: int = 5
    RETRY_BACKOFF_MULTIPLIER: int = 2


class FunctionSettings(BaseModel):
    class ZipFileSettings(BaseModel):
        MAX_FILES_ALLOWED: int = 2000
        DEFAULT_MAX_FILE_SIZE: int = 5 * 1024 * 1024  # 5MB

    DEFAULT_PROJECT_NAME: str = "my_function"
    DEFAULT_MAIN_FILE_NAME: str = "main"
    PROJECT_METADATA_FILE: str = "manifest.yaml"
    TEMPLATES_PATH: Path = (
        Path(__file__).resolve().parent.parent / "cli" / "functions" / "templates"
    )
    MAX_TIMEOUT_SECONDS: int = 300
    DEFAULT_CRON: str = "* * * * *"
    ZIP_FILE: ZipFileSettings = ZipFileSettings()


class Settings(BaseSettings):
    CONFIG: ConfigSettings = ConfigSettings()
    REQUESTS: RequestSettings = RequestSettings()
    FUNCTIONS: FunctionSettings = FunctionSettings()


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
