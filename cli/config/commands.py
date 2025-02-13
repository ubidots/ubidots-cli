from typing import Annotated

import typer

from cli.commons.styles import custom_prompt
from cli.config import handlers
from cli.config.models import AuthHeaderTypeEnum
from cli.settings import settings


def get_interactive_configuration() -> dict:
    profile = custom_prompt(
        "Profile",
        type=str,
        default="",
        mandatory=True,
        error_message="Profile name is mandatory. Please provide a value.",
    )
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
    original_token, masked_token = handlers.get_access_token_configuration(
        profile=profile
    )
    access_token_input = custom_prompt(
        "Access Token",
        type=str,
        default=masked_token,
        hide_input=True,
    )
    is_token_unchanged = not access_token_input or access_token_input == masked_token
    access_token = original_token if is_token_unchanged else access_token_input

    return {
        "profile": profile,
        "api_domain": api_domain,
        "auth_method_key": auth_method_key,
        "access_token": access_token,
    }


def config(
    default: Annotated[
        str,
        typer.Option(
            "--default",
            "-d",
            help=("Set the given profile as the default profile."),
        ),
    ] = "",
    interactive: Annotated[
        bool,
        typer.Option(
            "--no-interactive",
            "-n",
            help=(
                "Disable interactive mode and create config file with default values."
            ),
        ),
    ] = settings.CONFIG.DEFAULT_INTERACTIVE,
    profile: Annotated[
        str,
        typer.Option(
            "--profile",
            "-p",
            help=("Creates a new profile with the given name."),
        ),
    ] = "",
    domain: Annotated[
        str,
        typer.Option(
            "--api-domain",
            "-a",
            help=("Set the given profile as the default profile."),
        ),
    ] = settings.CONFIG.API_DOMAIN,
    token: Annotated[
        str,
        typer.Option(
            "--token",
            "-t",
            help=("Set the access token for the given profile."),
        ),
    ] = "",
    auth_method: Annotated[
        str,
        typer.Option(
            "--auth-method",
            "-m",
            help=("Set the access token for the given profile."),
        ),
    ] = AuthHeaderTypeEnum.TOKEN.name,
    verbose: bool = False,
):
    """
    1. `ubidots config --default <profile>` -> Marca el perfil indicado como default.
    2. `ubidots config` -> Crea un perfil de configuracion en modo interactivo.
        -> Pregunta por todos los parametros incluido el `profile`.
    3. `ubidots config --no-interactive --profile <profile> [--token <token> --api-domain <domain> --auth-method <method>]`
        -> Crea un perfil de configuracion en modo no interactivo con valores por defecto o vacios segun aplique.
    """
    # 1.
    if default:
        handlers.set_default_profile(profile=default)
    else:
        # 2.
        if interactive:
            config_details = get_interactive_configuration()
            handlers.set_configuration(**config_details)
        # 3.
        else:
            handlers.set_configuration(
                api_domain=domain,
                auth_method_key=auth_method,
                access_token=token,
                profile=profile,
            )
