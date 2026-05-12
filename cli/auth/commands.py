import os
import webbrowser
from typing import Annotated

import typer

from cli.auth.loopback_server import LoopbackServer
from cli.auth.loopback_server import assert_state_matches
from cli.auth.loopback_server import port_available
from cli.auth.oauth_client import build_authorize_url
from cli.auth.oauth_client import exchange_code_for_tokens
from cli.auth.oauth_client import generate_pkce_pair
from cli.auth.oauth_client import generate_state
from cli.commons.enums import MessageColorEnum
from cli.commons.exceptions import AuthorizationDeniedError
from cli.commons.exceptions import CSRFMismatchError
from cli.commons.exceptions import LoginTimeoutError
from cli.commons.exceptions import TokenExchangeError
from cli.commons.exceptions import UnknownOAuthClientError
from cli.config.helpers import get_configuration
from cli.config.helpers import save_profile_configuration
from cli.config.models import AuthHeaderTypeEnum
from cli.config.models import ProfileConfigModel
from cli.settings import settings

CLIENT_ID_ENV_VAR = "UBIDOTS_OAUTH_CLIENT_ID"


def _emit(message: str, color: MessageColorEnum = MessageColorEnum.SUCCESS) -> None:
    typer.echo(typer.style(message, fg=color, bold=True))


def _emit_error(message: str) -> None:
    typer.echo(typer.style(f"> [ERROR]: {message}", fg=MessageColorEnum.ERROR, bold=True), err=True)


def _resolve_active_config(profile: str | None) -> tuple[str, ProfileConfigModel]:
    try:
        config = get_configuration(profile=profile)
    except FileNotFoundError:
        config = ProfileConfigModel()
    profile_name = profile or settings.CONFIG.DEFAULT_PROFILE
    return profile_name, config


def _resolve_client_id(flag_value: str, current_config: ProfileConfigModel) -> str:
    return (
        flag_value
        or os.getenv(CLIENT_ID_ENV_VAR, "")
        or current_config.oauth_client_id
        or settings.OAUTH.DEFAULT_CLIENT_ID
    )


def _extract_user_label(token_set, fallback: str = "user") -> str:
    try:
        import base64
        import json

        parts = token_set.access_token.split(".")
        if len(parts) < 2:
            return fallback
        payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload_b64).decode("utf-8"))
        return claims.get("email") or claims.get("preferred_username") or claims.get("sub") or fallback
    except Exception:
        return fallback


def login(
    client_id: Annotated[
        str,
        typer.Option(
            "--client-id",
            "-c",
            help=(
                "OAuth2 client_id. Defaults to the env var "
                f"{CLIENT_ID_ENV_VAR}, then the profile's oauth_client_id, "
                "then the built-in default."
            ),
        ),
    ] = "",
    profile: Annotated[
        str,
        typer.Option(
            "--profile",
            "-p",
            help="Profile to populate. Defaults to the active profile.",
        ),
    ] = "",
    no_browser: Annotated[
        bool,
        typer.Option(
            "--no-browser",
            help="Print the authorization URL instead of opening a browser.",
        ),
    ] = False,
    scope: Annotated[
        str,
        typer.Option(
            "--scope",
            help="Space-separated list of OAuth scopes to request.",
        ),
    ] = "",
    timeout: Annotated[
        int,
        typer.Option(
            "--timeout",
            help="Seconds to wait for the browser callback.",
        ),
    ] = 0,
) -> None:
    profile_name, current_config = _resolve_active_config(profile or None)
    resolved_client_id = _resolve_client_id(client_id, current_config)
    if not resolved_client_id:
        _emit_error(
            "No OAuth client_id available. Pass --client-id, set the env var "
            f"{CLIENT_ID_ENV_VAR}, or ask DevOps for the ubidots-cli client_id."
        )
        raise typer.Exit(2)
    api_domain = current_config.api_domain or settings.CONFIG.API_DOMAIN
    requested_scope = scope or settings.OAUTH.DEFAULT_SCOPE
    timeout_seconds = timeout if timeout > 0 else settings.OAUTH.LOGIN_TIMEOUT_SECONDS

    if not port_available():
        _emit_error(
            f"Port {settings.OAUTH.LOOPBACK_PORT} is already in use. "
            "Close the process holding it and try again."
        )
        raise typer.Exit(2)

    pkce = generate_pkce_pair()
    state = generate_state()
    authorize_url = build_authorize_url(
        api_domain=api_domain,
        client_id=resolved_client_id,
        state=state,
        code_challenge=pkce.challenge,
        scope=requested_scope,
    )

    try:
        server = LoopbackServer()
    except OSError as exc:
        _emit_error(f"Could not bind loopback server: {exc}")
        raise typer.Exit(2) from exc

    if no_browser:
        typer.echo("Open the following URL in your browser to continue login:")
        typer.echo(authorize_url)
    else:
        typer.echo(f"Opening your browser to authenticate (profile: {profile_name})...")
        opened = webbrowser.open(authorize_url, new=1, autoraise=True)
        if not opened:
            typer.echo("Could not open a browser automatically. Open this URL manually:")
            typer.echo(authorize_url)

    try:
        result = server.wait_for_callback(timeout=timeout_seconds)
    except AuthorizationDeniedError:
        _emit_error(str(AuthorizationDeniedError()))
        raise typer.Exit(1) from None
    except LoginTimeoutError:
        _emit_error(str(LoginTimeoutError()))
        raise typer.Exit(1) from None

    try:
        assert_state_matches(result.state, state)
    except CSRFMismatchError as exc:
        _emit_error(str(exc))
        raise typer.Exit(1) from exc

    try:
        token_set = exchange_code_for_tokens(
            api_domain=api_domain,
            client_id=resolved_client_id,
            code=result.code,
            code_verifier=pkce.verifier,
        )
    except UnknownOAuthClientError as exc:
        _emit_error(str(exc))
        raise typer.Exit(1) from exc
    except TokenExchangeError as exc:
        _emit_error(str(exc))
        raise typer.Exit(1) from exc

    new_config = current_config.model_copy(
        update={
            "auth_method": AuthHeaderTypeEnum.OAUTH2,
            "access_token": token_set.access_token,
            "refresh_token": token_set.refresh_token,
            "expires_at": token_set.expires_at,
            "scope": token_set.scope or requested_scope,
            "token_type": token_set.token_type,
            "oauth_client_id": resolved_client_id,
        }
    )
    save_profile_configuration(profile=profile_name, config_model=new_config)

    user_label = _extract_user_label(token_set, fallback=profile_name)
    _emit(f"Login successful as {user_label}", color=MessageColorEnum.SUCCESS)
    raise typer.Exit(0)


if __name__ == "__main__":  # pragma: no cover
    typer.run(login)
