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
    visible_chars: int = settings.CONFIG.VISIBLE_SECRET_CHARS,
    fixed_length: int = settings.CONFIG.FIXED_LENGTH,
) -> str:
    visible_part = token[-visible_chars:]
    return visible_part.rjust(fixed_length, "*")
