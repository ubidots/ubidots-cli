from cli.commons.styles import custom_prompt
from cli.config import handlers
from cli.config.models import AuthHeaderTypeEnum
from cli.settings import settings


def config():
    api_domain = custom_prompt(
        "API Domain",
        type=str,
        default=settings.CONFIG.API_DOMAIN,
    )
    auth_method_key = custom_prompt(
        "Authentication Method",
        type=str,
        default=AuthHeaderTypeEnum.TOKEN.name,
    )
    original_token, masked_token = handlers.get_access_token_configuration()
    access_token_input = custom_prompt(
        "Access Token",
        type=str,
        default=masked_token,
        hide_input=True,
    )
    is_token_unchanged = not access_token_input or access_token_input == masked_token
    access_token = original_token if is_token_unchanged else access_token_input

    handlers.set_configuration(
        api_domain=api_domain,
        auth_method_key=auth_method_key,
        access_token=access_token,
    )
