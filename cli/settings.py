from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings

from cli.commons.enums import OutputFormatFieldsEnum


class ConfigSettings(BaseModel):
    API_DOMAIN: str = "https://industrial.api.ubidots.com"
    DIRECTORY_PATH: Path = Path.home() / ".ubidots_cli"
    FILE_PATH: Path = DIRECTORY_PATH / "config.yaml"
    VISIBLE_SECRET_CHARS: int = 4
    FIXED_LENGTH: int = 10
    DEFAULT_OUTPUT_FORMAT: OutputFormatFieldsEnum = (
        OutputFormatFieldsEnum.get_default_format()
    )


class FunctionSettings(BaseModel):
    DEFAULT_PROJECT_NAME: str = "my_function"
    DEFAULT_MAIN_FILE_NAME: str = "main"
    DEFAULT_MAIN_FUNCTION_NAME: str = "main"
    DEFAULT_HANDLER_FILE_NAME: str = "handler"
    DEFAULT_HANDLER_FUNCTION_NAME: str = "main"
    PROJECT_METADATA_FILE: str = ".manifest.yaml"
    BASE_PATH: Path = Path(__file__).resolve().parent.parent / "cli" / "functions"
    TEMPLATES_PATH: Path = BASE_PATH / "templates"
    HANDLERS_PATH: Path = BASE_PATH / "lambda_handlers"
    DEFAULT_TIMEOUT_SECONDS: int = 10
    MAX_TIMEOUT_SECONDS: int = 300
    DEFAULT_CRON: str = ""
    DEFAULT_HAS_CORS: bool = False
    DEFAULT_IS_RAW: bool = False
    CONTAINER_STARTUP_DELAY_SECONDS: float = 3


class Settings(BaseSettings):
    CONFIG: ConfigSettings = ConfigSettings()
    FUNCTIONS: FunctionSettings = FunctionSettings()


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
