import time
from collections.abc import Callable
from pathlib import Path

import filelock

from cli.auth.oauth_client import refresh_access_token
from cli.auth.redaction import register_secret
from cli.commons.exceptions import RefreshLockTimeoutError
from cli.config.enums import AuthHeaderTypeEnum
from cli.config.helpers import read_cli_configuration
from cli.config.helpers import save_profile_configuration
from cli.config.models import ProfileConfigModel
from cli.settings import settings


def _lock_path(profile: str) -> Path:
    return settings.CONFIG.PROFILES_PATH / f".lock-{profile}"


def ensure_fresh_token(
    profile: str,
    config: ProfileConfigModel,
    now: Callable[[], int] = lambda: int(time.time()),
) -> ProfileConfigModel:
    # AC10: Return unchanged if not OAUTH2
    if config.auth_method != AuthHeaderTypeEnum.OAUTH2:
        return config

    current_time = now()
    time_until_expiry = config.expires_at - current_time

    # NFR2: Short-circuit if token is fresh
    if time_until_expiry >= settings.OAUTH.REFRESH_LEEWAY_SECONDS:
        return config

    # Acquire lock with single-flight semantics
    lock_path = _lock_path(profile)
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    lock = filelock.FileLock(str(lock_path), timeout=settings.OAUTH.REFRESH_LOCK_TIMEOUT_SECONDS)

    try:
        lock.acquire()
    except filelock.Timeout as e:
        raise RefreshLockTimeoutError from e

    try:
        # AC4/AC6: Re-read from disk to avoid double refresh (single-flight)
        fresh_config = read_cli_configuration(profile)

        # Re-check expiry after acquiring lock
        current_time = now()
        time_until_expiry = fresh_config.expires_at - current_time

        # If another process already refreshed, skip network call
        if time_until_expiry >= settings.OAUTH.REFRESH_LEEWAY_SECONDS:
            return fresh_config

        # AC1: Trigger exactly one /o/token/ call across concurrent processes
        token_set = refresh_access_token(
            api_domain=fresh_config.api_domain,
            client_id=fresh_config.oauth_client_id,
            refresh_token=fresh_config.refresh_token,
        )

        # AC3: Build new config and persist before releasing lock
        updated_config = fresh_config.model_copy(
            update={
                "access_token": token_set.access_token,
                "refresh_token": token_set.refresh_token,
                "expires_at": token_set.expires_at,
                "token_type": token_set.token_type,
                "scope": token_set.scope,
            }
        )

        save_profile_configuration(profile, updated_config)

        # Register new tokens with redaction if a session is active
        register_secret(token_set.access_token)
        register_secret(token_set.refresh_token)

        return updated_config

    finally:
        lock.release()
