from pathlib import Path
from typing import tuple

import requests
import yaml
from pydantic import ValidationError

from cli.commons.exceptions import NoProfileError
from cli.commons.utils import exit_with_error_message
from cli.commons.utils import load_yaml
from cli.config.models import ProfileConfigModel
from cli.settings import settings


def save_profile_configuration(profile: str, config_model: ProfileConfigModel) -> None:
    file_path = Path(settings.CONFIG.PROFILES_PATH / f"{profile}.yaml")
    settings.CONFIG.PROFILES_PATH.mkdir(parents=True, exist_ok=True)
    with file_path.open("w") as config_file:
        yaml.dump(config_model.to_yaml_serializable_format(), config_file)


def exists_default_profile() -> bool:
    return Path(settings.CONFIG.PROFILES_PATH / "default.yaml").exists()


def create_default_profile() -> None:
    file_path: Path = Path(settings.CONFIG.PROFILES_PATH / "default.yaml")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w") as config_file:
        yaml.dump(ProfileConfigModel().to_yaml_serializable_format(), config_file)


def exist_config_file() -> bool:
    return Path(settings.CONFIG.FILE_PATH).exists()


def create_config_file() -> None:
    file_path: Path = Path(settings.CONFIG.FILE_PATH)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    config_data = {
        "profilesPath": str(settings.CONFIG.PROFILES_PATH),
        "profile": str(settings.CONFIG.DEFAULT_PROFILE),
        "ignoreFunctionsFile": str(settings.CONFIG.IGNORE_FUNCTIONS_FILE),
    }
    with file_path.open("w") as config_file:
        yaml.dump(config_data, config_file)


def validate_profile(profile: str):
    profile = profile.strip().strip('"').strip("'")
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


def read_cli_configuration(profile: str) -> ProfileConfigModel:
    file_path = Path(settings.CONFIG.PROFILES_PATH / f"{profile}.yaml")
    with file_path.open() as config_file:
        config_data = yaml.safe_load(config_file)
    return ProfileConfigModel(**config_data)


def get_active_profile_configuration() -> ProfileConfigModel:
    config = load_yaml(settings.CONFIG.FILE_PATH)

    profiles_path, profile = extract_profile_paths(config, settings.CONFIG.FILE_PATH)
    profile_file = Path(profiles_path) / f"{profile}.yaml"

    profile_config = load_yaml(profile_file)
    is_valid, missing_fields = validate_required_fields(profile_config, profile_file)

    if not is_valid:
        error_msg = (
            f"Missing required fields in {profile_file}: {', '.join(missing_fields)}"
        )
        raise ValueError(error_msg)

    return validate_profile_config(profile_config, profile_file)


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


def extract_profile_paths(config: dict, config_file: Path) -> tuple[str, str]:
    profiles_path = config.get("profilesPath")
    profile = config.get("profile")

    if not profiles_path or not profile:
        error_message = f"Invalid configuration: Missing 'profilesPath' or 'profile' in {config_file}"
        raise ValueError(error_message)
    return profiles_path, profile


def validate_required_fields(
    profile_config: dict, profile_file: Path
) -> tuple[bool, set]:
    required_fields = set(ProfileConfigModel.model_fields.keys())
    missing_fields = required_fields - profile_config.keys()
    if missing_fields:
        return False, missing_fields
    return True, set()


def validate_profile_config(
    profile_config: dict, profile_file: Path
) -> ProfileConfigModel:
    try:
        return ProfileConfigModel(**profile_config)
    except ValidationError as e:
        error_message = f"Invalid profile configuration in {profile_file}:\n{e}"
        raise ValueError(error_message) from e
