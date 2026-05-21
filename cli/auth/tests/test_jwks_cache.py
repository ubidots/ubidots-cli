import base64
import json
import os
import shutil
import stat
import tempfile
import time
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock
from unittest.mock import patch

import httpx
import pytest
import respx
from cryptography.hazmat.primitives.asymmetric import rsa

from cli.auth.exceptions import InvalidTokenSignatureError
from cli.auth.exceptions import JwksUnavailableError
from cli.auth.jwks_cache import JwksCachePath
from cli.auth.jwks_cache import JwksTTLSeconds
from cli.auth.jwks_cache import decode_jwt
from cli.auth.jwks_cache import fetch_jwks

SAMPLE_JWKS = {"keys": [{"kty": "RSA", "kid": "test-key"}]}


class TestJwksCachePath(TestCase):
    def test_absolute_path_accepted(self):
        p = JwksCachePath(Path(tempfile.gettempdir()) / "jwks.json")
        self.assertIsInstance(p.value, Path)

    def test_relative_path_is_rejected(self):
        with pytest.raises(ValueError):
            JwksCachePath(Path("relative/path.json"))


class TestJwksTTLSeconds(TestCase):
    def test_positive_value_accepted(self):
        self.assertEqual(JwksTTLSeconds(3600), 3600)

    def test_zero_is_rejected(self):
        with pytest.raises(ValueError):
            JwksTTLSeconds(0)

    def test_negative_value_is_rejected(self):
        with pytest.raises(ValueError):
            JwksTTLSeconds(-1)


class TestFetchJwks(TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._tmp_path = Path(self._tmp)

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_returns_cached_when_fresh(self):
        cache_file = self._tmp_path / "jwks.json"
        cache_file.write_text(json.dumps(SAMPLE_JWKS))
        cache_path = JwksCachePath(cache_file)
        ttl = JwksTTLSeconds(3600)
        result = fetch_jwks(
            api_domain="https://core.test",
            cache_path=cache_path,
            ttl=ttl,
            now=lambda: cache_file.stat().st_mtime + 1,
        )
        self.assertEqual(result, SAMPLE_JWKS)

    @respx.mock
    def test_stale_cache_is_refreshed_from_remote(self):
        cache_file = self._tmp_path / "jwks.json"
        cache_file.write_text(json.dumps({"keys": []}))
        cache_path = JwksCachePath(cache_file)
        ttl = JwksTTLSeconds(60)
        respx.get("https://core.test/o/.well-known/jwks.json").mock(return_value=httpx.Response(200, json=SAMPLE_JWKS))
        result = fetch_jwks(
            api_domain="https://core.test",
            cache_path=cache_path,
            ttl=ttl,
            now=lambda: cache_file.stat().st_mtime + 9999,
        )
        self.assertEqual(result, SAMPLE_JWKS)
        self.assertEqual(json.loads(cache_file.read_text()), SAMPLE_JWKS)
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(cache_file.stat().st_mode), 0o600)

    @respx.mock
    def test_network_failure_falls_back_to_stale_cache(self):
        cache_file = self._tmp_path / "jwks.json"
        cache_file.write_text(json.dumps(SAMPLE_JWKS))
        cache_path = JwksCachePath(cache_file)
        ttl = JwksTTLSeconds(1)
        respx.get("https://core.test/o/.well-known/jwks.json").mock(side_effect=httpx.ConnectError("unreachable"))
        result = fetch_jwks(
            api_domain="https://core.test",
            cache_path=cache_path,
            ttl=ttl,
            now=lambda: cache_file.stat().st_mtime + 9999,
        )
        self.assertEqual(result, SAMPLE_JWKS)

    @respx.mock
    def test_unavailable_remote_without_cache_raises_error(self):
        cache_path = JwksCachePath(self._tmp_path / "jwks.json")
        ttl = JwksTTLSeconds(60)
        respx.get("https://core.test/o/.well-known/jwks.json").mock(side_effect=httpx.ConnectError("unreachable"))
        with pytest.raises(JwksUnavailableError):
            fetch_jwks(api_domain="https://core.test", cache_path=cache_path, ttl=ttl)

    @respx.mock
    def test_corrupt_cache_is_ignored_and_remote_is_fetched(self):
        cache_file = self._tmp_path / "jwks.json"
        cache_file.write_text("NOT VALID JSON{{{{")
        cache_path = JwksCachePath(cache_file)
        ttl = JwksTTLSeconds(3600)
        respx.get("https://core.test/o/.well-known/jwks.json").mock(return_value=httpx.Response(200, json=SAMPLE_JWKS))
        result = fetch_jwks(
            api_domain="https://core.test",
            cache_path=cache_path,
            ttl=ttl,
            now=lambda: cache_file.stat().st_mtime + 1,
        )
        self.assertEqual(result, SAMPLE_JWKS)


class TestDecodeJwt(TestCase):
    def test_malformed_token_is_rejected(self):
        with pytest.raises(InvalidTokenSignatureError):
            decode_jwt("only.two", jwks=SAMPLE_JWKS)

    def test_unsigned_token_is_rejected(self):
        header = base64.urlsafe_b64encode(b'{"alg":"none","kid":"k"}').rstrip(b"=").decode()
        payload = base64.urlsafe_b64encode(b'{"sub":"x"}').rstrip(b"=").decode()
        token = f"{header}.{payload}.sig"
        with pytest.raises(InvalidTokenSignatureError):
            decode_jwt(token, jwks=SAMPLE_JWKS, algorithms=("RS256",))

    def test_non_rsa_algorithm_is_rejected(self):
        header = base64.urlsafe_b64encode(b'{"alg":"HS256","kid":"k"}').rstrip(b"=").decode()
        payload = base64.urlsafe_b64encode(b'{"sub":"x"}').rstrip(b"=").decode()
        token = f"{header}.{payload}.sig"
        with pytest.raises(InvalidTokenSignatureError):
            decode_jwt(token, jwks=SAMPLE_JWKS, algorithms=("RS256",))

    def test_absent_claims_have_safe_defaults(self):
        minimal_jwk = {"kty": "RSA", "kid": "k"}
        mock_key = MagicMock()
        mock_pyjwk = MagicMock()
        mock_pyjwk.key = mock_key
        with (
            patch("cli.auth.jwks_cache.jwt.PyJWK", return_value=mock_pyjwk),
            patch("cli.auth.jwks_cache.jwt.decode", return_value={}),
            patch("cli.auth.jwks_cache.jwt.get_unverified_header", return_value={"alg": "RS256", "kid": "k"}),
        ):
            claims = decode_jwt("a.b.c", jwks={"keys": [minimal_jwk]})
        self.assertEqual(claims.email, "")
        self.assertEqual(claims.user_type, "")
        self.assertEqual(claims.business_account, "")
        self.assertEqual(claims.scope, "")
        self.assertEqual(claims.exp, 0)

    def test_valid_signature_returns_decoded_claims(self):
        import jwt

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()
        test_claims = {
            "email": "test@example.com",
            "user_type": "business",
            "business_account": "test-account",
            "scope": "read write",
            "exp": int(time.time()) + 3600,
            "sub": "test-subject",
        }
        token = jwt.encode(test_claims, private_key, algorithm="RS256", headers={"kid": "test-key-id"})
        pub_nums = public_key.public_numbers()
        n_bytes = pub_nums.n.to_bytes((pub_nums.n.bit_length() + 7) // 8, byteorder="big")
        e_bytes = pub_nums.e.to_bytes((pub_nums.e.bit_length() + 7) // 8, byteorder="big")
        jwks = {
            "keys": [
                {
                    "kty": "RSA",
                    "kid": "test-key-id",
                    "use": "sig",
                    "n": base64.urlsafe_b64encode(n_bytes).rstrip(b"=").decode("utf-8"),
                    "e": base64.urlsafe_b64encode(e_bytes).rstrip(b"=").decode("utf-8"),
                }
            ]
        }
        claims = decode_jwt(token, jwks=jwks)
        self.assertEqual(claims.email, "test@example.com")
        self.assertEqual(claims.user_type, "business")
        self.assertEqual(claims.business_account, "test-account")
        self.assertEqual(claims.scope, "read write")
        self.assertEqual(claims.exp, test_claims["exp"])
