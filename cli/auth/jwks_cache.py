from __future__ import annotations

import contextlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from cli.settings import settings


@dataclass(frozen=True)
class CachedJWKS:
    data: dict
    fetched_at: int

    def is_expired(self, ttl_seconds: int) -> bool:
        return time.time() - self.fetched_at > ttl_seconds


def _load_cached(cache_path: Path) -> CachedJWKS | None:
    if not cache_path.exists():
        return None
    try:
        with cache_path.open() as f:
            payload = json.load(f)
        return CachedJWKS(
            data=payload["jwks"],
            fetched_at=int(payload["fetched_at"]),
        )
    except (OSError, ValueError, KeyError):
        return None


def _write_cache(cache_path: Path, jwks: dict) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"jwks": jwks, "fetched_at": int(time.time())}
    fd = os.open(
        str(cache_path),
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        0o600,
    )
    with os.fdopen(fd, "w") as f:
        json.dump(payload, f)
    with contextlib.suppress(OSError):
        cache_path.chmod(0o600)


def fetch_jwks(
    api_domain: str,
    cache_path: Path | None = None,
    ttl_seconds: int | None = None,
    http_client: httpx.Client | None = None,
) -> dict | None:
    cache_path = cache_path or settings.OAUTH.JWKS_CACHE_PATH
    ttl = ttl_seconds if ttl_seconds is not None else settings.OAUTH.JWKS_CACHE_TTL_SECONDS

    cached = _load_cached(cache_path)
    if cached and not cached.is_expired(ttl):
        return cached.data

    url = f"{api_domain.rstrip('/')}{settings.OAUTH.JWKS_PATH}"
    client = http_client or httpx.Client(timeout=5.0)
    owns_client = http_client is None
    try:
        response = client.get(url)
    except httpx.HTTPError:
        return cached.data if cached else None
    finally:
        if owns_client:
            client.close()

    if response.status_code != httpx.codes.OK:
        return cached.data if cached else None
    try:
        jwks = response.json()
    except ValueError:
        return cached.data if cached else None

    with contextlib.suppress(OSError):
        _write_cache(cache_path, jwks)
    return jwks
