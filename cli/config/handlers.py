import typer

from cli.config.helpers import save_cli_configuration
from cli.config.models import APIConfigModel
from cli.config.models import AuthHeaderType


def handler_config(api_domain: str, auth_method_key: AuthHeaderType, access_token: str):
    try:
        auth_method_value = AuthHeaderType[auth_method_key].value
    except KeyError as error:
        auth_method_options = [method.name for method in AuthHeaderType]
        valid_options = ", ".join(auth_method_options)
        typer.echo(
            f"Error: '{auth_method_key}' is not a valid Authentication Method. "
            f"Valid options are: {valid_options}"
        )
        raise typer.Exit(1) from error

    save_cli_configuration(
        APIConfigModel(
            api_domain=api_domain,
            auth_method=auth_method_value,
            access_token=access_token,
        )
    )
    typer.echo("Configuration saved successfully.")
