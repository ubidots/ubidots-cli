from urllib.parse import quote_plus
from urllib.parse import urlencode

import yaml

from cli.auth.token_refresh import ensure_fresh_token
from cli.commons.exceptions import RefreshLockTimeoutError
from cli.commons.exceptions import RefreshTokenInvalidGrantError
from cli.commons.exceptions import RefreshTokenNetworkError
from cli.commons.exceptions import RefreshTokenRemoteError
from cli.commons.http_auth import get_auth_headers
from cli.commons.utils import exit_with_error_message
from cli.config.helpers import extract_profile_paths
from cli.config.models import ProfileConfigModel
from cli.settings import settings


def _get_active_profile_name() -> str:
    if not settings.CONFIG.FILE_PATH.exists():
        return settings.CONFIG.DEFAULT_PROFILE

    try:
        config_data = yaml.safe_load(settings.CONFIG.FILE_PATH.read_text(encoding="utf-8"))
        _, profile = extract_profile_paths(config_data, settings.CONFIG.FILE_PATH)
    except Exception as error:
        raise RuntimeError(f"Failed to read config from {settings.CONFIG.FILE_PATH}: {error}") from error

    return profile


def build_endpoint(
    route: str,
    active_config: ProfileConfigModel,
    query_params: dict | None = None,
    **kwargs,
) -> tuple[str, dict]:
    try:
        profile_name = _get_active_profile_name()
        refreshed_config = ensure_fresh_token(profile=profile_name, config=active_config)
    except (
        RefreshTokenInvalidGrantError,
        RefreshTokenRemoteError,
        RefreshTokenNetworkError,
        RefreshLockTimeoutError,
        RuntimeError,
    ) as error:
        exit_with_error_message(error)

    url = f"{refreshed_config.api_domain}{route.format(**kwargs)}"
    if query_params:
        filter_string = query_params.get("filter")
        non_filter = {k: v for k, v in query_params.items() if k != "filter" and v is not None}
        query_string = urlencode(non_filter, doseq=True)
        if query_string:
            url += f"?{query_string}"
        if filter_string:
            url += ("&" if query_string else "?") + quote_plus(filter_string, safe="=")

    headers = get_auth_headers(refreshed_config)
    return url, headers
