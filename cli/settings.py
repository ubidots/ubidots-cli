from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings

from cli.commons.enums import OutputFormatFieldsEnum
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.enums import FunctionMethodEnum
from cli.functions.enums import FunctionRuntimeLayerTypeEnum


class ConfigSettings(BaseModel):
    API_DOMAIN: str = "https://industrial.api.ubidots.com"
    RUNTIMES_URL: str = f"{API_DOMAIN}/api/-/functions/_/runtimes"
    DIRECTORY_PATH: Path = Path.home() / ".ubidots_cli"
    PROFILES_PATH: Path = DIRECTORY_PATH / "profiles"
    FILE_PATH: Path = DIRECTORY_PATH / "config.yaml"
    VISIBLE_SECRET_CHARS: int = 4
    FIXED_LENGTH: int = 10
    DEFAULT_OUTPUT_FORMAT: OutputFormatFieldsEnum = (
        OutputFormatFieldsEnum.get_default_format()
    )
    DEFAULT_PROFILE: str = "default"
    DEFAULT_INTERACTIVE: bool = True
    IGNORE_FUNCTIONS_FILE: Path = DIRECTORY_PATH / "functions.ignore"
    DEFAULT_CONTAINER_REPOSITORY: str = "https://registry.hub.docker.com/library/"
    DEFAULT_CONTAINER_ENGINE: str = FunctionEngineTypeEnum.DOCKER.value
    DEFAULT_RUNTIMES: list[str] = []
    ENABLED_LANGUAGES: list[str] = [e.value for e in FunctionLanguageEnum]


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
    ENABLED_LANGUAGES: list[str] = [e.value for e in FunctionLanguageEnum]
    DEFAULT_LANGUAGE: str = FunctionLanguageEnum.NODEJS.value
    DEFAULT_RUNTIME: str = FunctionRuntimeLayerTypeEnum.NODEJS_20_LITE.value
    DEFAULT_IS_SECURE: bool = False
    DEFAULT_HTTP_ENABLED: bool = False
    DEFAULT_METHODS: list[FunctionMethodEnum] = [FunctionMethodEnum.GET]


class Settings(BaseSettings):
    CONFIG: ConfigSettings = ConfigSettings()
    FUNCTIONS: FunctionSettings = FunctionSettings()


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
