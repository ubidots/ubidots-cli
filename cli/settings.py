from pathlib import Path

# Config: API configuration settings.
UBIDOTS_API_DOMAIN = "https://industrial.api.ubidots.com"
UBIDOTS_CONFIG_PATH = Path.home() / ".ubidots_cli"
UBIDOTS_ACCESS_CONFIG_FILE = UBIDOTS_CONFIG_PATH / "config.yaml"
UBIDOTS_CONFIG_FOLDER = Path.home() / ".ubidots_cli"
UBIDOTS_ACCESS_CONFIG_FILE = UBIDOTS_CONFIG_FOLDER / "config.yaml"

# Functions: Default settings for functions projects.
UBIDOTS_FUNCTIONS_DEFAULT_PROJECT_NAME = "my_function"
UBIDOTS_FUNCTIONS_DEFAULT_MAIN_FILE_NAME = "main"
UBIDOTS_FUNCTIONS_PROJECT_METADATA_FILE = "manifest.yaml"
UBIDOTS_FUNCTIONS_TEMPLATES_PATH = (
    Path(__file__).resolve().parent.parent / "cli" / "functions" / "templates"
)
## Server-dependent settings. Ensure to sync with Ubidots server constraints.
UBIDOTS_FUNCTIONS_MAX_FILES_ALLOWED = 2000
UBIDOTS_FUNCTIONS_DEFAULT_MAX_FILE_SIZE = 5 * 1024 * 1024
