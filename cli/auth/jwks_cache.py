from __future__ import annotations

import json
import time
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Self

import httpx
import jwt

from cli.auth.enums import AlgorithmEnum
from cli.auth.exceptions import InvalidTokenSignatureError
from cli.auth.exceptions import JwksUnavailableError
from cli.settings import settings

_STANDARD_TOKEN_PARTS = 3


@dataclass(frozen=True, slots=True)
class JwksCachePath:
    value: Path

    def __post_init__(self) -> None:
        if not self.value.is_absolute():
            error_message = f"JWKS cache path must be absolute, got: {self.value}"
            raise ValueError(error_message)


class JwksTTLSeconds(int):
    def __new__(cls, value: int) -> Self:
        if value <= 0:
            error_message = f"JWKS TTL must be > 0, got: {value}"
            raise ValueError(error_message)
        return super().__new__(cls, value)


@dataclass(frozen=True, slots=True)
class JwtClaims:
    email: str
    user_type: str
    business_account: str
    scope: str
    exp: int
    raw: dict


def fetch_jwks(
    api_domain: str,
    cache_path: JwksCachePath,
    ttl: JwksTTLSeconds,
    http_client: httpx.Client | None = None,
    now: Callable[[], float] = time.time,
) -> dict:
    current_time = now()

    if cache_path.value.exists():
        with suppress(OSError, json.JSONDecodeError):
            mtime = cache_path.value.stat().st_mtime
            if current_time - mtime < ttl:
                with Path(cache_path.value).open(encoding="utf-8") as file:
                    return json.load(file)

    url = f"{api_domain.rstrip('/')}{settings.OAUTH.JWKS_PATH}"
    client = http_client or httpx.Client(timeout=10.0)
    owns_client = http_client is None

    try:
        response = client.get(url)
        response.raise_for_status()
        jwks = response.json()

        with suppress(OSError):
            cache_path.value.parent.mkdir(parents=True, exist_ok=True)
            cache_path.value.parent.chmod(0o700)
            cache_path.value.write_text(json.dumps(jwks))
            cache_path.value.chmod(0o600)

        return jwks
    except (httpx.HTTPError, json.JSONDecodeError):
        if cache_path.value.exists():
            with suppress(OSError, json.JSONDecodeError), Path(cache_path.value).open(encoding="utf-8") as file:
                return json.load(file)
        raise JwksUnavailableError from None
    finally:
        if owns_client:
            client.close()


def decode_jwt(token: str, jwks: dict, algorithms: tuple[AlgorithmEnum, ...] = (AlgorithmEnum.RS256,)) -> JwtClaims:
    parts = token.split(".")
    if len(parts) != _STANDARD_TOKEN_PARTS:
        error_message = "Invalid token format"
        raise InvalidTokenSignatureError(error_message)

    try:
        header = jwt.get_unverified_header(token)
    except jwt.DecodeError as error:
        error_message = "Invalid token header"
        raise InvalidTokenSignatureError(error_message) from error

    alg = header.get("alg")
    if alg not in algorithms or alg == AlgorithmEnum.NONE:
        error_message = f"Unsupported algorithm: {alg}"
        raise InvalidTokenSignatureError(error_message)

    if not (keys := jwks.get("keys", [])):
        error_message = "No keys available in JWKS"
        raise InvalidTokenSignatureError(error_message)

    if kid := header.get("kid"):
        try:
            signing_key = JwksClient(jwks).get_signing_key(kid)
        except jwt.PyJWKClientError as error:
            error_message = f"Could not find signing key: {error}"
            raise InvalidTokenSignatureError(error_message) from error

        try:
            payload = jwt.decode(
                token,
                key=signing_key.key,
                options={"verify_signature": True, "verify_exp": False, "verify_aud": False},
                algorithms=algorithms,
            )
        except (jwt.InvalidSignatureError, jwt.InvalidKeyError, jwt.DecodeError) as error:
            error_message = f"Signature verification failed: {error}"
            raise InvalidTokenSignatureError(error_message) from error
    else:
        last_error = None
        for key_data in keys:
            try:
                signing_key = jwt.PyJWK(key_data)
                payload = jwt.decode(
                    token,
                    key=signing_key.key,
                    options={"verify_signature": True, "verify_exp": False, "verify_aud": False},
                    algorithms=algorithms,
                )
                break
            except (jwt.InvalidSignatureError, jwt.InvalidKeyError, jwt.DecodeError, jwt.PyJWKClientError) as error:
                last_error = error
                continue
        else:
            error_message = f"Token signature verification failed with all available keys: {last_error}"
            raise InvalidTokenSignatureError(error_message)

    return JwtClaims(
        email=payload.get("email", ""),
        user_type=payload.get("user_type", ""),
        business_account=payload.get("business_account", ""),
        scope=payload.get("scope", ""),
        exp=payload.get("exp", 0),
        raw=payload,
    )


class JwksClient:
    def __init__(self, jwks: dict) -> None:
        self.jwks = jwks

    def get_signing_key(self, kid: str):
        keys = self.jwks.get("keys", [])

        if kid:
            for key in keys:
                if key.get("kid") == kid:
                    return jwt.PyJWK(key)
            raise jwt.PyJWKClientError(f"No key found for kid {kid}")

        if not keys:
            error_message = "No keys available in JWKS"
            raise jwt.PyJWKClientError(error_message)

        return jwt.PyJWK(keys[0])
