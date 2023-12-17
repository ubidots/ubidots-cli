import typer

from cli import settings
from cli.commons.styles import custom_prompt
from cli.config.models import APIConfigModel, AuthHeaderType
from cli.config.utils import save_cli_configuration


def config():
    api_domain = custom_prompt(
        "API Domain",
        type=str,
        default=settings.UBIDOTS_API_DOMAIN,
    )
    auth_method = custom_prompt(
        "Authentication Method",
        type=str,
        default=AuthHeaderType.TOKEN.value,
    )
    access_token = custom_prompt(
        "Access Token",
        type=str,
        hide_input=True,
    )
    save_cli_configuration(
        APIConfigModel(
            api_domain=api_domain,
            auth_method=auth_method,
            access_token=access_token,
        )
    )
    typer.echo("Configuration saved successfully.")
