from pathlib import Path

import requests
import yaml
from pydantic import ValidationError

from cli.commons.exceptions import CurrentPlanDoesNotIncludeRuntimes
from cli.commons.exceptions import InvalidProfileError
from cli.commons.exceptions import NoProfileError
from cli.commons.exceptions import ProfileConfigEmptyFieldsError
from cli.commons.exceptions import ProfileConfigMissingFieldsError
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


def get_profile_configuration(profile: str) -> ProfileConfigModel:
    profile_path = Path(settings.CONFIG.PROFILES_PATH / f"{profile}.yaml")
    profile_config = load_yaml(profile_path)
    return validate_profile_config(profile_config, profile_path)


def get_active_profile_configuration() -> ProfileConfigModel:
    config = load_yaml(settings.CONFIG.FILE_PATH)
    profiles_path, profile = extract_profile_paths(config, settings.CONFIG.FILE_PATH)
    profile_file = Path(profiles_path) / f"{profile}.yaml"
    profile_config = load_yaml(profile_file)
    return validate_profile_config(profile_config, profile_file)


def get_configuration(profile: str | None = None) -> ProfileConfigModel:
    return (
        get_profile_configuration(profile=profile)
        if profile
        else get_active_profile_configuration()
    )


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

        error_message = f"Unexpected response format: {type(runtimes)} - {runtimes}"
        raise ValueError(error_message)

    except requests.RequestException as e:
        if e.response is not None and e.response.status_code == 402:
            exit_with_error_message(
                exception=CurrentPlanDoesNotIncludeRuntimes(),
            )
        return []  # Log or handle the error as needed

    except ValueError:
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


def validate_profile_config(
    profile_config: dict, profile_file: Path
) -> ProfileConfigModel:

    required_fields = set(ProfileConfigModel.model_fields.keys())
    missing_fields = required_fields - profile_config.keys()
    if missing_fields:
        raise ProfileConfigMissingFieldsError(
            missing_fields=missing_fields,
            profile_file=profile_file,
        )

    empty_fields = {
        field
        for field in required_fields
        if field in profile_config and not profile_config[field]
    }
    if empty_fields:
        raise ProfileConfigEmptyFieldsError(
            empty_fields=empty_fields, profile_file=profile_file
        )

    try:
        return ProfileConfigModel(**profile_config)
    except ValidationError as e:
        raise InvalidProfileError(profile=str(profile_file), exception=e) from e
