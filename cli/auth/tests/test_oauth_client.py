import base64
import hashlib
import time
from unittest import TestCase
from urllib.parse import parse_qs
from urllib.parse import urlparse

import httpx
import pytest
import respx

from cli.auth.enums import TokenTypeEnum
from cli.auth.oauth_client import PKCEPair
from cli.auth.oauth_client import RevokeResult
from cli.auth.oauth_client import RevokeTokenPayload
from cli.auth.oauth_client import build_authorize_url
from cli.auth.oauth_client import exchange_code_for_tokens
from cli.auth.oauth_client import generate_pkce_pair
from cli.auth.oauth_client import generate_state
from cli.auth.oauth_client import refresh_access_token
from cli.auth.oauth_client import revoke_refresh_token
from cli.commons.exceptions import RefreshTokenInvalidGrantError
from cli.commons.exceptions import RefreshTokenNetworkError
from cli.commons.exceptions import RefreshTokenRemoteError
from cli.commons.exceptions import RevokeNetworkError
from cli.commons.exceptions import RevokeRemoteError
from cli.commons.exceptions import TokenExchangeError
from cli.commons.exceptions import UnknownOAuthClientError
from cli.settings import settings

_REFRESH_API_DOMAIN = "https://core.example.com"
_REFRESH_TOKEN_URL = f"{_REFRESH_API_DOMAIN}/o/token/"
_CLIENT_ID = "ubidots-cli"
_OLD_REFRESH_TOKEN = "old-refresh-token"


class TestGeneratePKCEPair(TestCase):
    def test_pair_uses_s256_method_and_consistent_challenge_for_its_verifier(self):
        pair = generate_pkce_pair()
        expected_challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(pair.verifier.encode("ascii")).digest())
            .rstrip(b"=")
            .decode("ascii")
        )
        expected_pair = PKCEPair(
            verifier=pair.verifier,
            challenge=expected_challenge,
            method="S256",
        )
        self.assertEqual(pair, expected_pair)

    def test_verifier_length_is_within_rfc_7636_bounds(self):
        rfc_min = 43
        rfc_max = 128
        verifier_length = len(generate_pkce_pair().verifier)
        self.assertGreaterEqual(verifier_length, rfc_min)
        self.assertLessEqual(verifier_length, rfc_max)

    def test_two_pairs_have_distinct_verifiers(self):
        first_verifier = generate_pkce_pair().verifier
        second_verifier = generate_pkce_pair().verifier
        self.assertNotEqual(first_verifier, second_verifier)


class TestGenerateState(TestCase):
    def test_two_states_are_unique_and_meet_minimum_length(self):
        minimum_length = 32
        first_state = generate_state()
        second_state = generate_state()
        self.assertNotEqual(first_state, second_state)
        self.assertGreaterEqual(len(first_state), minimum_length)
        self.assertGreaterEqual(len(second_state), minimum_length)


class TestBuildAuthorizeURL(TestCase):
    def test_authorize_url_contains_full_expected_param_set(self):
        api_domain = "https://industrial.api.ubidots.com"
        expected_query = {
            "response_type": ["code"],
            "client_id": ["ubidots-cli"],
            "redirect_uri": [settings.OAUTH.REDIRECT_URI],
            "scope": ["read write"],
            "state": ["state-xyz"],
            "code_challenge": ["challenge-xyz"],
            "code_challenge_method": ["S256"],
        }
        actual_url = build_authorize_url(
            api_domain=api_domain,
            client_id="ubidots-cli",
            state="state-xyz",
            code_challenge="challenge-xyz",
            scope="read write",
        )
        parsed = urlparse(actual_url)
        actual_query = parse_qs(parsed.query)
        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.netloc, "industrial.api.ubidots.com")
        self.assertEqual(parsed.path, settings.OAUTH.AUTHORIZE_PATH)
        self.assertEqual(actual_query, expected_query)

    def test_redirect_uri_uses_127_0_0_1_loopback_per_rfc_8252(self):
        expected_redirect_substring = "127.0.0.1"
        forbidden_redirect_substring = "localhost"
        actual_url = build_authorize_url(
            api_domain="https://industrial.api.ubidots.com",
            client_id="ubidots-cli",
            state="s",
            code_challenge="c",
        )
        actual_redirect_uri = parse_qs(urlparse(actual_url).query)["redirect_uri"][0]
        self.assertIn(expected_redirect_substring, actual_redirect_uri)
        self.assertNotIn(forbidden_redirect_substring, actual_redirect_uri)


class TestExchangeCodeForTokens:
    @respx.mock
    def test_happy_path_returns_full_token_set(self):
        response_body = {
            "access_token": "jwt-access",
            "refresh_token": "opaque-refresh",
            "token_type": TokenTypeEnum.BEARER,
            "expires_in": 900,
            "scope": "read write",
        }
        respx.post("https://core.test/o/token/").mock(return_value=httpx.Response(200, json=response_body))
        actual_tokens = exchange_code_for_tokens(
            api_domain="https://core.test",
            client_id="ubidots-cli",
            code="the-code",
            code_verifier="verifier",
        )
        assert actual_tokens.access_token == "jwt-access"
        assert actual_tokens.refresh_token == "opaque-refresh"
        assert actual_tokens.token_type == TokenTypeEnum.BEARER
        assert actual_tokens.scope == "read write"
        assert actual_tokens.expires_at > 0

    @respx.mock
    def test_401_response_raises_unknown_oauth_client_error(self):
        respx.post("https://core.test/o/token/").mock(
            return_value=httpx.Response(401, json={"error": "invalid_client"})
        )
        with pytest.raises(UnknownOAuthClientError):
            exchange_code_for_tokens(
                api_domain="https://core.test",
                client_id="ubidots-cli",
                code="c",
                code_verifier="v",
            )

    @respx.mock
    def test_400_invalid_grant_raises_token_exchange_error_with_detail(self):
        respx.post("https://core.test/o/token/").mock(
            return_value=httpx.Response(
                400,
                json={"error": "invalid_grant", "error_description": "Code expired"},
            )
        )
        with pytest.raises(TokenExchangeError) as excinfo:
            exchange_code_for_tokens(
                api_domain="https://core.test",
                client_id="ubidots-cli",
                code="c",
                code_verifier="v",
            )
        assert "Code expired" in str(excinfo.value)

    @respx.mock
    def test_generic_client_word_in_error_does_not_misclassify_as_unknown_client(self):
        # Setup — only the exact OAuth2 code `invalid_client` should raise UnknownOAuthClientError.
        # Generic phrases like "Client-side validation" must propagate as TokenExchangeError.
        respx.post("https://core.test/o/token/").mock(
            return_value=httpx.Response(
                400,
                json={
                    "error": "invalid_request",
                    "error_description": "Client-side validation failed",
                },
            )
        )
        with pytest.raises(TokenExchangeError):
            exchange_code_for_tokens(
                api_domain="https://core.test",
                client_id="ubidots-cli",
                code="c",
                code_verifier="v",
            )

    @respx.mock
    def test_request_body_contains_pkce_verifier_and_authorization_code_grant(self):
        expected_pairs = {
            "grant_type": "authorization_code",
            "code": "THECODE",
            "code_verifier": "THEVERIFIER",
            "client_id": "ubidots-cli",
            "redirect_uri": settings.OAUTH.REDIRECT_URI,
        }
        route = respx.post("https://core.test/o/token/").mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "a",
                    "refresh_token": "r",
                    "expires_in": 10,
                    "token_type": TokenTypeEnum.BEARER,
                },
            )
        )
        exchange_code_for_tokens(
            api_domain="https://core.test",
            client_id="ubidots-cli",
            code="THECODE",
            code_verifier="THEVERIFIER",
        )
        sent_body = route.calls[0].request.content.decode("utf-8")
        actual_pairs = {k: v[0] for k, v in parse_qs(sent_body).items()}
        assert actual_pairs == expected_pairs


class TestRevokeTokenPayloadToDict(TestCase):
    def test_serializes_all_required_revocation_fields(self):
        payload = RevokeTokenPayload(token="tok", client_id="cli-id")
        self.assertEqual(
            payload.to_dict(),
            {"token": "tok", "client_id": "cli-id", "token_type_hint": "refresh_token"},
        )

    def test_accepts_custom_token_type_hint(self):
        payload = RevokeTokenPayload(token="tok", client_id="cli-id", token_type_hint="access_token")
        self.assertEqual(payload.to_dict()["token_type_hint"], "access_token")


class TestRevokeRefreshToken:
    @respx.mock
    def test_successful_revocation_returns_ok(self):
        respx.post("https://core.test/o/revoke_token/").mock(return_value=httpx.Response(200))
        result = revoke_refresh_token(api_domain="https://core.test", client_id="ubidots-cli", refresh_token="rt")
        assert result == RevokeResult(status="ok", http_status=200)

    @pytest.mark.parametrize("status_code", [401, 404])
    @respx.mock
    def test_rejected_token_treated_as_already_revoked(self, status_code):
        respx.post("https://core.test/o/revoke_token/").mock(return_value=httpx.Response(status_code))
        result = revoke_refresh_token(api_domain="https://core.test", client_id="ubidots-cli", refresh_token="rt")
        assert result == RevokeResult(status="already_invalid", http_status=status_code)

    @pytest.mark.parametrize("status_code", [400, 403])
    @respx.mock
    def test_revocation_failure_propagates_as_remote_error(self, status_code):
        respx.post("https://core.test/o/revoke_token/").mock(return_value=httpx.Response(status_code))
        with pytest.raises(RevokeRemoteError):
            revoke_refresh_token(api_domain="https://core.test", client_id="ubidots-cli", refresh_token="rt")

    @respx.mock
    def test_server_error_propagates_as_remote_error(self):
        respx.post("https://core.test/o/revoke_token/").mock(return_value=httpx.Response(500))
        with pytest.raises(RevokeRemoteError):
            revoke_refresh_token(api_domain="https://core.test", client_id="ubidots-cli", refresh_token="rt")

    @respx.mock
    def test_unreachable_server_propagates_as_network_error(self):
        respx.post("https://core.test/o/revoke_token/").mock(side_effect=httpx.ConnectError("connection refused"))
        with pytest.raises(RevokeNetworkError):
            revoke_refresh_token(api_domain="https://core.test", client_id="ubidots-cli", refresh_token="rt")

    @respx.mock
    def test_request_uses_oauth2_revocation_protocol_format(self):
        route = respx.post("https://core.test/o/revoke_token/").mock(return_value=httpx.Response(200))
        revoke_refresh_token(api_domain="https://core.test", client_id="ubidots-cli", refresh_token="my-rt")
        request = route.calls[0].request
        assert request.headers["content-type"] == "application/x-www-form-urlencoded"
        body = request.content.decode()
        assert "token=my-rt" in body
        assert "client_id=ubidots-cli" in body


class TestRevokeExceptionsStr(TestCase):
    def test_network_error_message_mentions_remote_revocation(self):
        self.assertIn("Could not reach core to revoke remotely", str(RevokeNetworkError()))

    def test_remote_error_has_non_empty_default_message(self):
        self.assertNotEqual(str(RevokeRemoteError()), "")

    def test_remote_error_includes_provided_detail(self):
        self.assertIn("something went wrong", str(RevokeRemoteError(detail="something went wrong")))


class TestRefreshAccessTokenExceptionsStr(TestCase):
    def test_invalid_grant_message_instructs_user_to_log_in_again(self):
        self.assertEqual(
            str(RefreshTokenInvalidGrantError()),
            "Your session has expired. Please run 'ubidots login' again.",
        )

    def test_remote_error_message_includes_provided_detail(self):
        self.assertEqual(str(RefreshTokenRemoteError(detail="server boom")), "Could not refresh session: server boom")

    def test_network_error_message_includes_api_domain(self):
        self.assertEqual(
            str(RefreshTokenNetworkError(api_domain=_REFRESH_API_DOMAIN)),
            f"Cannot reach Ubidots core at {_REFRESH_API_DOMAIN}. Check your network.",
        )


class TestRefreshAccessTokenHappyPath(TestCase):
    @respx.mock
    def test_returns_new_access_and_refresh_tokens(self):
        now = int(time.time())
        respx.post(_REFRESH_TOKEN_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "new-access",
                    "refresh_token": "new-refresh",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                    "scope": "read write",
                },
            )
        )
        token_set = refresh_access_token(
            api_domain=_REFRESH_API_DOMAIN,
            client_id=_CLIENT_ID,
            refresh_token=_OLD_REFRESH_TOKEN,
        )
        self.assertEqual(token_set.access_token, "new-access")
        self.assertEqual(token_set.refresh_token, "new-refresh")
        self.assertGreaterEqual(token_set.expires_at, now + 3600)

    @respx.mock
    def test_falls_back_to_input_refresh_token_when_omitted_from_response(self):
        respx.post(_REFRESH_TOKEN_URL).mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "new-access", "expires_in": 3600, "token_type": "Bearer", "scope": "read write"},
            )
        )
        token_set = refresh_access_token(
            api_domain=_REFRESH_API_DOMAIN,
            client_id=_CLIENT_ID,
            refresh_token=_OLD_REFRESH_TOKEN,
        )
        self.assertEqual(token_set.refresh_token, _OLD_REFRESH_TOKEN)

    @respx.mock
    def test_caller_provided_http_client_is_not_closed(self):
        from unittest.mock import MagicMock

        client = MagicMock(spec=httpx.Client)
        client.post.return_value = httpx.Response(
            200,
            json={"access_token": "a", "expires_in": 60, "token_type": "Bearer", "scope": ""},
        )
        refresh_access_token(
            api_domain=_REFRESH_API_DOMAIN,
            client_id=_CLIENT_ID,
            refresh_token=_OLD_REFRESH_TOKEN,
            http_client=client,
        )
        client.close.assert_not_called()


def _do_refresh() -> None:
    refresh_access_token(
        api_domain=_REFRESH_API_DOMAIN,
        client_id=_CLIENT_ID,
        refresh_token=_OLD_REFRESH_TOKEN,
    )


class TestRefreshAccessTokenErrors(TestCase):
    @respx.mock
    def test_invalid_grant_response_raises_invalid_grant_error(self):
        respx.post(_REFRESH_TOKEN_URL).mock(return_value=httpx.Response(400, json={"error": "invalid_grant"}))
        with pytest.raises(RefreshTokenInvalidGrantError):
            _do_refresh()

    @respx.mock
    def test_non_invalid_grant_4xx_raises_remote_error_with_description(self):
        respx.post(_REFRESH_TOKEN_URL).mock(
            return_value=httpx.Response(400, json={"error": "invalid_client", "error_description": "bad client"})
        )
        with pytest.raises(RefreshTokenRemoteError) as exc_info:
            _do_refresh()
        self.assertEqual(exc_info.value.detail, "bad client")

    @respx.mock
    def test_4xx_without_description_uses_error_field_as_detail(self):
        respx.post(_REFRESH_TOKEN_URL).mock(return_value=httpx.Response(400, json={"error": "unsupported_grant_type"}))
        with pytest.raises(RefreshTokenRemoteError) as exc_info:
            _do_refresh()
        self.assertEqual(exc_info.value.detail, "unsupported_grant_type")

    @respx.mock
    def test_non_json_error_response_raises_remote_error_with_http_status(self):
        respx.post(_REFRESH_TOKEN_URL).mock(return_value=httpx.Response(403, content=b"forbidden"))
        with pytest.raises(RefreshTokenRemoteError) as exc_info:
            _do_refresh()
        self.assertIn("403", exc_info.value.detail)

    @respx.mock
    def test_connection_error_raises_network_error_with_api_domain(self):
        respx.post(_REFRESH_TOKEN_URL).mock(side_effect=httpx.ConnectError("refused"))
        with pytest.raises(RefreshTokenNetworkError) as exc_info:
            _do_refresh()
        self.assertEqual(exc_info.value.api_domain, _REFRESH_API_DOMAIN)

    @respx.mock
    def test_timeout_raises_network_error(self):
        respx.post(_REFRESH_TOKEN_URL).mock(side_effect=httpx.TimeoutException("timeout"))
        with pytest.raises(RefreshTokenNetworkError):
            _do_refresh()

    @respx.mock
    def test_5xx_non_json_raises_remote_error_with_http_status(self):
        respx.post(_REFRESH_TOKEN_URL).mock(return_value=httpx.Response(500, content=b"Internal Server Error"))
        with pytest.raises(RefreshTokenRemoteError) as exc_info:
            _do_refresh()
        self.assertIn("500", exc_info.value.detail)
