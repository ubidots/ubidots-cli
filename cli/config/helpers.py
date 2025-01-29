from pathlib import Path

import requests
import yaml

from cli.commons.exceptions import NoProfileError
from cli.commons.utils import exit_with_error_message
from cli.config.models import APIConfigModel
from cli.settings import settings


def save_cli_configuration(profile: str, config_model: APIConfigModel) -> None:
    file_path = Path(settings.CONFIG.PROFILES_PATH / f"{profile}.yaml")
    settings.CONFIG.PROFILES_PATH.mkdir(parents=True, exist_ok=True)
    with file_path.open("w") as config_file:
        yaml.dump(config_model.to_yaml_serializable_format(), config_file)


def create_default_profile() -> None:
    file_path: Path = Path(settings.CONFIG.PROFILES_PATH / "default.yaml")
    if file_path.exists():
        return
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w") as config_file:
        yaml.dump(APIConfigModel().to_yaml_serializable_format(), config_file)


def create_config_file() -> None:
    file_path: Path = Path(settings.CONFIG.FILE_PATH)
    if file_path.exists():
        return
    file_path.parent.mkdir(parents=True, exist_ok=True)
    config_data = {
        "profilesPath": str(settings.CONFIG.PROFILES_PATH),
        "profile": str(settings.CONFIG.DEFAULT_PROFILE),
        "ignoreFunctionsFile": str(settings.CONFIG.IGNORE_FUNCTIONS_FILE),
    }
    with file_path.open("w") as config_file:
        yaml.dump(config_data, config_file)


def validate_profile(profile: str):
    if not profile.strip():
        exit_with_error_message(
            exception=NoProfileError(),
        )


def overwrite_default_profile(profile: str) -> None:
    file_path = Path(settings.CONFIG.FILE_PATH)
    with file_path.open("r") as config_file:
        config_data = yaml.safe_load(config_file)
    config_data["profile"] = profile
    with file_path.open("w") as config_file:
        yaml.safe_dump(config_data, config_file)


def read_cli_configuration(profile: str) -> APIConfigModel:
    file_path: Path = Path(settings.CONFIG.PROFILES_PATH / f"{profile}.yaml")
    with file_path.open() as config_file:
        config_data = yaml.safe_load(config_file)
    return APIConfigModel(**config_data)


def mask_token(
    token: str,
    visible_chars: int = settings.CONFIG.VISIBLE_SECRET_CHARS,
    fixed_length: int = settings.CONFIG.FIXED_LENGTH,
) -> str:
    visible_part = token[-visible_chars:]
    return visible_part.rjust(fixed_length, "*")


def get_runtimes_from_api(access_token: str) -> list[dict]:
    headers = {"X-Auth-Token": access_token}
    try:
        response = requests.get(settings.CONFIG.RUNTIMES_URL, headers=headers)
        response.raise_for_status()
        runtimes = response.json()
        if isinstance(runtimes, list):
            return runtimes
        error_message = "Unexpected response format"
        raise ValueError(error_message)
    except (requests.RequestException, ValueError):
        return []


def profile_exists(profile: str) -> bool:
    return Path(settings.CONFIG.PROFILES_PATH / f"{profile}.yaml").exists()
