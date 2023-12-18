from pathlib import Path

# Config: API configuration settings.
UBIDOTS_API_DOMAIN = "https://industrial.api.ubidots.com"
UBIDOTS_CONFIG_PATH = Path.home() / ".ubidots_cli"
UBIDOTS_ACCESS_CONFIG_FILE = UBIDOTS_CONFIG_PATH / "config.yaml"
