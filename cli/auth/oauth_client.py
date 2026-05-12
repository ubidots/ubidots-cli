import base64
import hashlib
import secrets
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from cli.commons.exceptions import TokenExchangeError
from cli.commons.exceptions import UnknownOAuthClientError
from cli.settings import settings


@dataclass(frozen=True)
class PKCEPair:
    verifier: str
    challenge: str
    method: str = "S256"


@dataclass(frozen=True)
class TokenSet:
    access_token: str
    refresh_token: str
    token_type: str
    expires_at: int
    scope: str


def generate_pkce_pair() -> PKCEPair:
    verifier = secrets.token_urlsafe(settings.OAUTH.VERIFIER_BYTES)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return PKCEPair(verifier=verifier, challenge=challenge)


def generate_state() -> str:
    return secrets.token_urlsafe(settings.OAUTH.STATE_BYTES)


def build_authorize_url(
    api_domain: str,
    client_id: str,
    state: str,
    code_challenge: str,
    scope: str | None = None,
    redirect_uri: str | None = None,
) -> str:
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri or settings.OAUTH.REDIRECT_URI,
        "scope": scope or settings.OAUTH.DEFAULT_SCOPE,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{api_domain.rstrip('/')}{settings.OAUTH.AUTHORIZE_PATH}?{urlencode(params)}"


def exchange_code_for_tokens(
    api_domain: str,
    client_id: str,
    code: str,
    code_verifier: str,
    redirect_uri: str | None = None,
    http_client: httpx.Client | None = None,
) -> TokenSet:
    url = f"{api_domain.rstrip('/')}{settings.OAUTH.TOKEN_PATH}"
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri or settings.OAUTH.REDIRECT_URI,
        "client_id": client_id,
        "code_verifier": code_verifier,
    }

    client = http_client or httpx.Client(timeout=10.0)
    owns_client = http_client is None
    try:
        response = client.post(
            url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    finally:
        if owns_client:
            client.close()

    if response.status_code == httpx.codes.UNAUTHORIZED:
        raise UnknownOAuthClientError
    if response.status_code != httpx.codes.OK:
        detail = _safe_error_detail(response)
        if "invalid_client" in detail:
            raise UnknownOAuthClientError
        raise TokenExchangeError(detail=detail)

    data = response.json()
    expires_in = int(data.get("expires_in", 0))
    return TokenSet(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token", ""),
        token_type=data.get("token_type", "Bearer"),
        expires_at=int(time.time()) + expires_in,
        scope=data.get("scope", ""),
    )


def _safe_error_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return f"HTTP {response.status_code}"
    if isinstance(body, dict):
        return body.get("error_description") or body.get("error") or f"HTTP {response.status_code}"
    return f"HTTP {response.status_code}"
