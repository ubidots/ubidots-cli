import json
import stat
import sys
import time

import httpx
import pytest
import respx

from cli.auth.jwks_cache import fetch_jwks


@pytest.fixture
def cache_path(tmp_path):
    return tmp_path / "cache" / "jwks.json"


class TestFetchJWKS:
    @respx.mock
    def test_first_call_fetches_from_remote_and_writes_cache(self, cache_path):
        # Setup
        expected_jwks = {"keys": [{"kty": "RSA", "kid": "k1", "n": "abc"}]}
        respx.get("https://core.test/o/.well-known/jwks.json").mock(
            return_value=httpx.Response(200, json=expected_jwks)
        )
        # Action
        actual_jwks = fetch_jwks(
            api_domain="https://core.test",
            cache_path=cache_path,
            ttl_seconds=3600,
        )
        # Expected
        assert actual_jwks == expected_jwks
        assert cache_path.exists()
        cached_payload = json.loads(cache_path.read_text())
        assert cached_payload["jwks"] == expected_jwks
        assert isinstance(cached_payload["fetched_at"], int)

    @respx.mock
    def test_cache_hit_skips_remote_fetch(self, cache_path):
        # Setup
        cached_jwks = {"keys": [{"kty": "RSA", "kid": "k1", "n": "cached"}]}
        cache_path.parent.mkdir(parents=True)
        cache_path.write_text(
            json.dumps({"jwks": cached_jwks, "fetched_at": int(time.time())})
        )
        route = respx.get("https://core.test/o/.well-known/jwks.json").mock(
            return_value=httpx.Response(200, json={"keys": []})
        )
        # Action
        actual_jwks = fetch_jwks(
            api_domain="https://core.test",
            cache_path=cache_path,
            ttl_seconds=3600,
        )
        # Expected
        assert actual_jwks == cached_jwks
        assert route.call_count == 0

    @respx.mock
    def test_expired_cache_triggers_refetch(self, cache_path):
        # Setup
        cache_path.parent.mkdir(parents=True)
        cache_path.write_text(
            json.dumps(
                {
                    "jwks": {"keys": [{"kid": "stale"}]},
                    "fetched_at": int(time.time()) - 7200,
                }
            )
        )
        fresh_jwks = {"keys": [{"kid": "fresh"}]}
        respx.get("https://core.test/o/.well-known/jwks.json").mock(
            return_value=httpx.Response(200, json=fresh_jwks)
        )
        # Action
        actual_jwks = fetch_jwks(
            api_domain="https://core.test",
            cache_path=cache_path,
            ttl_seconds=3600,
        )
        # Expected
        assert actual_jwks == fresh_jwks

    @respx.mock
    def test_network_error_falls_back_to_stale_cache_when_present(self, cache_path):
        # Setup
        stale_jwks = {"keys": [{"kid": "stale-but-usable"}]}
        cache_path.parent.mkdir(parents=True)
        cache_path.write_text(
            json.dumps(
                {"jwks": stale_jwks, "fetched_at": int(time.time()) - 7200}
            )
        )
        respx.get("https://core.test/o/.well-known/jwks.json").mock(
            side_effect=httpx.ConnectError("boom")
        )
        # Action
        actual_jwks = fetch_jwks(
            api_domain="https://core.test",
            cache_path=cache_path,
            ttl_seconds=3600,
        )
        # Expected
        assert actual_jwks == stale_jwks

    @respx.mock
    def test_network_error_with_no_cache_returns_none(self, cache_path):
        # Setup
        respx.get("https://core.test/o/.well-known/jwks.json").mock(
            side_effect=httpx.ConnectError("boom")
        )
        # Action
        actual_jwks = fetch_jwks(
            api_domain="https://core.test",
            cache_path=cache_path,
            ttl_seconds=3600,
        )
        # Expected
        assert actual_jwks is None

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only")
    @respx.mock
    def test_cache_file_is_written_with_mode_0600(self, cache_path):
        # Setup
        respx.get("https://core.test/o/.well-known/jwks.json").mock(
            return_value=httpx.Response(200, json={"keys": []})
        )
        expected_mode = 0o600
        # Action
        fetch_jwks(
            api_domain="https://core.test",
            cache_path=cache_path,
            ttl_seconds=3600,
        )
        actual_mode = stat.S_IMODE(cache_path.stat().st_mode)
        # Expected
        assert actual_mode == expected_mode
