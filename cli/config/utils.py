import yaml

from cli import settings
from cli.config.models import APIConfigModel


def save_cli_configuration(config_model: APIConfigModel) -> None:
    config_path = settings.UBIDOTS_CONFIG_PATH
    config_file = settings.UBIDOTS_ACCESS_CONFIG_FILE

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, "w") as file:
        yaml.dump(config_model.for_yaml_dump(), file)


def read_cli_configuration() -> APIConfigModel:
    config_file = settings.UBIDOTS_ACCESS_CONFIG_FILE

    with open(config_file) as file:
        config_data = yaml.safe_load(file)
    return APIConfigModel(**config_data)
