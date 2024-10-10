from cli.commons.exceptions import InvalidOptionError
from cli.commons.utils import exit_with_error_message
from cli.commons.utils import exit_with_success_message
from cli.config.helpers import mask_token
from cli.config.helpers import read_cli_configuration
from cli.config.helpers import save_cli_configuration
from cli.config.models import APIConfigModel
from cli.config.models import AuthHeaderTypeEnum


def set_configuration(
    api_domain: str,
    auth_method_key: AuthHeaderTypeEnum,
    access_token: str,
):
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

    save_cli_configuration(
        APIConfigModel(
            api_domain=api_domain,
            auth_method=auth_method_value,
            access_token=access_token,
        )
    )
    exit_with_success_message(message="Configuration saved successfully.")


def get_access_token_configuration() -> tuple[str, str]:
    try:
        config_data = read_cli_configuration()
    except FileNotFoundError:
        return str(None), str(None)

    original_token = config_data.access_token
    masked_token = mask_token(token=original_token)
    return original_token, masked_token
