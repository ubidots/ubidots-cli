import yaml

from cli.config.models import APIConfigModel
from cli.settings import settings


def save_cli_configuration(config_model: APIConfigModel) -> None:
    config_directory_path = settings.CONFIG.DIRECTORY_PATH
    config_file_path = settings.CONFIG.FILE_PATH

    config_directory_path.mkdir(parents=True, exist_ok=True)
    with open(config_file_path, "w") as config_file:
        yaml.dump(config_model.to_yaml_serializable_format(), config_file)


def read_cli_configuration() -> APIConfigModel:
    config_file_path = settings.CONFIG.FILE_PATH

    with open(config_file_path) as config_file:
        config_data = yaml.safe_load(config_file)
    return APIConfigModel(**config_data)


def mask_token(token: str, visible_chars: int = 4) -> str:
    visible_chars = min(len(token), visible_chars)
    num_asterisks = len(token) - visible_chars
    return "*" * num_asterisks + token[-visible_chars:]
