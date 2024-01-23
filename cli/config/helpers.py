import yaml

from cli.config.models import APIConfigModel
from cli.settings import settings


def save_cli_configuration(config_model: APIConfigModel) -> None:
    config_path = settings.CONFIG.DIRECTORY_PATH
    config_file = settings.CONFIG.FILE_PATH

    config_path.mkdir(parents=True, exist_ok=True)
    with open(config_file, "w") as file:
        yaml.dump(config_model.for_yaml_dump(), file)


def read_cli_configuration() -> APIConfigModel:
    config_file = settings.CONFIG.FILE_PATH

    with open(config_file) as file:
        config_data = yaml.safe_load(file)
    return APIConfigModel(**config_data)


def mask_token(token: str, visible_chars: int = 4) -> str:
    visible_chars = min(len(token), visible_chars)
    num_asterisks = len(token) - visible_chars
    return "*" * num_asterisks + token[-visible_chars:]
