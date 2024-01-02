from cli.commons.styles import custom_prompt
from cli.config.handlers import handler_config
from cli.config.models import AuthHeaderType
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
        default=AuthHeaderType.TOKEN.name,
    )
    access_token = custom_prompt(
        "Access Token",
        type=str,
        hide_input=True,
    )
    handler_config(
        api_domain=api_domain,
        auth_method_key=auth_method_key,
        access_token=access_token,
    )
