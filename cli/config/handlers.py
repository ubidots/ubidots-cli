from cli.commons.exceptions import EmptyTokenError
from cli.commons.exceptions import InvalidOptionError
from cli.commons.exceptions import RuntimeNotFoundError
from cli.commons.exceptions import UnexistentProfileError
from cli.commons.styles import custom_prompt
from cli.commons.utils import exit_with_error_message
from cli.commons.utils import exit_with_success_message
from cli.config.helpers import create_config_file
from cli.config.helpers import create_default_profile
from cli.config.helpers import exist_config_file
from cli.config.helpers import exists_default_profile
from cli.config.helpers import get_runtimes_from_api
from cli.config.helpers import mask_token
from cli.config.helpers import overwrite_default_profile
from cli.config.helpers import profile_exists
from cli.config.helpers import read_cli_configuration
from cli.config.helpers import save_profile_configuration
from cli.config.helpers import validate_profile
from cli.config.models import AuthHeaderTypeEnum
from cli.config.models import ProfileConfigModel


def existing_profile(profile: str):
    if not profile_exists(profile):
        return
    profile_overwrite_confirmation = custom_prompt(
        "Profile already exists. Do you want to overwrite it? [y/n]",
        type=str,
        default="n",
    )
    if profile_overwrite_confirmation.lower() != "y":
        exit_with_error_message(
            exception=FileExistsError(
                "Profile already exists and user chose not to overwrite it. Aborting configuration."
            ),
        )


def get_runtimes(access_token: str) -> list[str]:
    try:
        runtimes: list[dict] = get_runtimes_from_api(access_token=access_token)
    except Exception:
        return []
    return [runtime["label"] for runtime in runtimes]


def set_default_profile(profile: str):
    validate_profile(profile=profile)
    if not profile_exists(profile):
        exit_with_error_message(
            exception=UnexistentProfileError(profile=profile),
        )
    overwrite_default_profile(profile=profile)
    exit_with_success_message(
        message=f"Profile {profile} was set as default successfully."
    )


def validate_auth_method(auth_method_key: str) -> AuthHeaderTypeEnum:
    try:
        auth_method_value = AuthHeaderTypeEnum[auth_method_key]
    except KeyError:
        exit_with_error_message(
            exception=InvalidOptionError(
                invalid_option=auth_method_key,
                valid_options=AuthHeaderTypeEnum,
                option_name="Authentication Method",
            ),
        )
    return auth_method_value


def set_configuration(
    api_domain: str,
    auth_method_key: str,
    access_token: str,
    profile: str,
):

    if not exist_config_file():
        create_config_file()

    if not exists_default_profile():
        create_default_profile()

    if not access_token:
        exit_with_error_message(exception=(EmptyTokenError()))

    # Check if a profile was provided and exit with error if not
    validate_profile(profile=profile)
    # If the profile already exists, ask the user if they want to overwrite it
    existing_profile(profile=profile)
    # Validate the authentication method key and get the corresponding value
    auth_method_value = validate_auth_method(auth_method_key=auth_method_key)
    # Get the user's runtimes from the API
    if not (runtimes := get_runtimes(access_token=access_token)):
        exit_with_error_message(
            exception=RuntimeNotFoundError(),
        )
    save_profile_configuration(
        profile=profile,
        config_model=ProfileConfigModel(
            api_domain=api_domain,
            auth_method=auth_method_value,
            access_token=access_token,
            runtimes=runtimes,
        ),
    )
    exit_with_success_message(message="Configuration saved successfully.")


def get_access_token_configuration(profile: str) -> tuple[str, str]:
    try:
        config_data = read_cli_configuration(profile=profile)
    except FileNotFoundError:
        return str(None), str(None)

    original_token = config_data.access_token
    masked_token = mask_token(token=original_token)
    return original_token, masked_token
