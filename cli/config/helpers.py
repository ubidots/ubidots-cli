import yaml

from cli.config.models import APIConfigModel
from cli.settings import settings


def save_cli_configuration(config_model: APIConfigModel) -> None:
    settings.CONFIG.DIRECTORY_PATH.mkdir(parents=True, exist_ok=True)
    with settings.CONFIG.FILE_PATH.open("w") as config_file:
        yaml.dump(config_model.to_yaml_serializable_format(), config_file)


def read_cli_configuration() -> APIConfigModel:
    with settings.CONFIG.FILE_PATH.open() as config_file:
        config_data = yaml.safe_load(config_file)
    return APIConfigModel(**config_data)


def mask_token(
    token: str,
    visible_chars: int = settings.CONFIG.DEFAULT_VISIBLE_TOKEN_CHARS,
) -> str:
    if visible_chars >= len(token):
        return "*" * len(token)

    num_asterisks = len(token) - visible_chars
    return "*" * num_asterisks + token[-visible_chars:]
