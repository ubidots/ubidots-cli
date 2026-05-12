from __future__ import annotations

import time
from pathlib import Path

import httpx
import yaml
from filelock import FileLock
from filelock import Timeout

from cli.commons.exceptions import CoreUnreachableError
from cli.commons.exceptions import RefreshFailedError
from cli.commons.exceptions import RefreshLockBusyError
from cli.commons.exceptions import RefreshTokenExpiredError
from cli.config.models import AuthHeaderTypeEnum
from cli.config.models import ProfileConfigModel
from cli.settings import settings


def needs_refresh(config: ProfileConfigModel, leeway_seconds: int | None = None) -> bool:
    if config.auth_method != AuthHeaderTypeEnum.OAUTH2:
        return False
    leeway = leeway_seconds if leeway_seconds is not None else settings.OAUTH.REFRESH_LEEWAY_SECONDS
    return config.expires_at - int(time.time()) < leeway


def _lock_path_for(profile_name: str) -> Path:
    return Path(settings.CONFIG.PROFILES_PATH) / f".lock-{profile_name}"


def _persist_refreshed(
    profile_name: str,
    base_config: ProfileConfigModel,
    response_body: dict,
    requested_at: int,
) -> ProfileConfigModel:
    from cli.config.helpers import save_profile_configuration

    expires_in = int(response_body.get("expires_in", 0))
    new_config = base_config.model_copy(
        update={
            "access_token": response_body["access_token"],
            "refresh_token": response_body.get("refresh_token") or base_config.refresh_token,
            "expires_at": requested_at + expires_in,
            "scope": response_body.get("scope") or base_config.scope,
            "token_type": response_body.get("token_type") or base_config.token_type or "Bearer",
        }
    )
    save_profile_configuration(profile=profile_name, config_model=new_config)
    return new_config


def _request_refresh(
    api_domain: str,
    client_id: str,
    refresh_token: str,
    http_client: httpx.Client | None,
) -> tuple[dict, int]:
    url = f"{api_domain.rstrip('/')}{settings.OAUTH.TOKEN_PATH}"
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
    }
    client = http_client or httpx.Client(timeout=settings.OAUTH.REFRESH_HTTP_TIMEOUT_SECONDS)
    owns_client = http_client is None
    requested_at = int(time.time())
    try:
        response = client.post(
            url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    except httpx.HTTPError as exc:
        raise CoreUnreachableError(api_domain=api_domain) from exc
    finally:
        if owns_client:
            client.close()

    if response.status_code == httpx.codes.OK:
        return response.json(), requested_at

    error_code, error_description = _error_fields(response)
    if 400 <= response.status_code < 500 and error_code == "invalid_grant":
        raise RefreshTokenExpiredError
    raise RefreshFailedError(
        detail=error_description or error_code or f"HTTP {response.status_code}"
    )


def _error_fields(response: httpx.Response) -> tuple[str, str]:
    try:
        body = response.json()
    except ValueError:
        return "", ""
    if not isinstance(body, dict):
        return "", ""
    return body.get("error", ""), body.get("error_description", "")


def ensure_fresh_token(
    profile_name: str,
    config: ProfileConfigModel,
    http_client: httpx.Client | None = None,
) -> ProfileConfigModel:
    if not needs_refresh(config):
        return config

    if not config.refresh_token:
        raise RefreshTokenExpiredError

    lock_path = _lock_path_for(profile_name)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(str(lock_path), timeout=settings.OAUTH.REFRESH_LOCK_TIMEOUT_SECONDS)

    from cli.config.helpers import read_cli_configuration

    try:
        with lock:
            try:
                latest_config = read_cli_configuration(profile=profile_name)
            except (OSError, yaml.YAMLError):
                latest_config = config

            if not needs_refresh(latest_config):
                return latest_config

            response_body, requested_at = _request_refresh(
                api_domain=latest_config.api_domain or settings.CONFIG.API_DOMAIN,
                client_id=latest_config.oauth_client_id or settings.OAUTH.DEFAULT_CLIENT_ID,
                refresh_token=latest_config.refresh_token,
                http_client=http_client,
            )
            return _persist_refreshed(
                profile_name=profile_name,
                base_config=latest_config,
                response_body=response_body,
                requested_at=requested_at,
            )
    except Timeout as exc:
        raise RefreshLockBusyError from exc
