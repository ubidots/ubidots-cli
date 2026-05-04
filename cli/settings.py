from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings

from cli.commons.enums import OutputFormatFieldsEnum
from cli.functions.constants import DEFAULT_RUNTIME as FUNCTIONS_DEFAULT_RUNTIME
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.enums import FunctionMethodEnum


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
    DEFAULT_RUNTIME: str = FUNCTIONS_DEFAULT_RUNTIME
    DEFAULT_IS_SECURE: bool = False
    DEFAULT_HTTP_ENABLED: bool = False
    DEFAULT_METHODS: list[FunctionMethodEnum] = [FunctionMethodEnum.GET]


class PagesSettings(BaseModel):
    DEFAULT_PAGE_NAME: str = "my_page"
    WORKSPACE_DIR_NAME: str = "pages"
    PROJECT_MANIFEST_FILE: str = "manifest.toml"
    PROJECT_METADATA_FILE: str = ".manifest.yaml"
    PAGE_INDEX_HTML_FILE: str = ".page.html"
    PROJECT_INDEX_HTML_FILE: str = "index.html"
    DEFAULT_PAGE_TYPE: str = "dashboard"  # Converted to PageTypeEnum in usage
    BASE_ENDPOINT: str = "/api/v2.0/pages"

    # Routing configuration
    ROUTING_MODE: str = "path"  # "subdomain", "port", or "path"

    # Hot reload configuration
    HOT_RELOAD_ENABLED: bool = True
    HOT_RELOAD_ENDPOINT: str = "/__dev/reload"  # SSE endpoint path
    HOT_RELOAD_PORT_DEFAULT: int = 9000
    HOT_RELOAD_PORT_FALLBACK_START: int = 9001
    HOT_RELOAD_WATCH_EXTENSIONS: list[str] = [
        ".html",
        ".css",
        ".js",
        ".json",
        ".toml",
        ".md",
        ".txt",
        ".py",
    ]
    HOT_RELOAD_IGNORE_PATTERNS: list[str] = [
        "*.pyc",
        "__pycache__",
        ".git",
        ".DS_Store",
        "*.tmp",
    ]
    HOT_RELOAD_DEBOUNCE_MS: int = 1000  # Debounce in milliseconds

    TEMPLATES_DIR: Path = (
        Path(__file__).resolve().parent.parent / "cli" / "pages" / "templates"
    )
    UBIDOTS_PAGE_LAYOUT_ZIP: dict[str, Path] = {
        "dashboard": TEMPLATES_DIR / "default-page.zip",
    }
    UBIDOTS_PAGE_HTML: dict[str, Path] = {
        "dashboard": TEMPLATES_DIR / "ubidots-page.html.template",
    }
    INDEX_HTML: dict[str, Path] = {
        "dashboard": TEMPLATES_DIR / "index.html.template",
    }

    API_ROUTES: dict[str, str] = {
        "base": BASE_ENDPOINT,  # GET/POST /api/v2.0/pages/
        "detail": f"{BASE_ENDPOINT}/{{page_key}}",  # GET /api/v2.0/pages/<page_key>
        "code": f"{BASE_ENDPOINT}/{{page_key}}/code",  # Upload/Download code
    }

    TEMPLATE_PLACEHOLDERS: dict[str, dict[str, str]] = {
        "dashboard": {
            "html_canvas_library_url": "https://ubidots.com/static/html-canvas-library.js",
            "react_url": "https://unpkg.com/react@18/umd/react.development.js",
            "react_dom_url": "https://unpkg.com/react-dom@18/umd/react-dom.development.js",
            "babel_standalone_url": "https://unpkg.com/@babel/standalone/babel.min.js",
            "vulcanui_js_url": "https://cdn.jsdelivr.net/npm/vulcanui@latest/dist/vulcanui.min.js",
            "vulcanui_css_url": "https://cdn.jsdelivr.net/npm/vulcanui@latest/dist/vulcanui.min.css",
        }
    }


class Settings(BaseSettings):
    CONFIG: ConfigSettings = ConfigSettings()
    FUNCTIONS: FunctionSettings = FunctionSettings()
    PAGES: PagesSettings = PagesSettings()


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
