import base64
import hashlib
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
from cli.auth.oauth_client import revoke_refresh_token
from cli.commons.exceptions import RevokeNetworkError
from cli.commons.exceptions import RevokeRemoteError
from cli.commons.exceptions import TokenExchangeError
from cli.commons.exceptions import UnknownOAuthClientError
from cli.settings import settings


class TestGeneratePKCEPair(TestCase):
    def test_pair_uses_s256_method_and_consistent_challenge_for_its_verifier(self):
        # Setup
        # (none)
        # Action
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
        # Expected
        self.assertEqual(pair, expected_pair)

    def test_verifier_length_is_within_rfc_7636_bounds(self):
        # Setup
        rfc_min = 43
        rfc_max = 128
        # Action
        verifier_length = len(generate_pkce_pair().verifier)
        # Expected
        self.assertGreaterEqual(verifier_length, rfc_min)
        self.assertLessEqual(verifier_length, rfc_max)

    def test_two_pairs_have_distinct_verifiers(self):
        # Setup
        # (none)
        # Action
        first_verifier = generate_pkce_pair().verifier
        second_verifier = generate_pkce_pair().verifier
        # Expected
        self.assertNotEqual(first_verifier, second_verifier)


class TestGenerateState(TestCase):
    def test_two_states_are_unique_and_meet_minimum_length(self):
        # Setup
        minimum_length = 32
        # Action
        first_state = generate_state()
        second_state = generate_state()
        # Expected
        self.assertNotEqual(first_state, second_state)
        self.assertGreaterEqual(len(first_state), minimum_length)
        self.assertGreaterEqual(len(second_state), minimum_length)


class TestBuildAuthorizeURL(TestCase):
    def test_authorize_url_contains_full_expected_param_set(self):
        # Setup
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
        # Action
        actual_url = build_authorize_url(
            api_domain=api_domain,
            client_id="ubidots-cli",
            state="state-xyz",
            code_challenge="challenge-xyz",
            scope="read write",
        )
        parsed = urlparse(actual_url)
        actual_query = parse_qs(parsed.query)
        # Expected
        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.netloc, "industrial.api.ubidots.com")
        self.assertEqual(parsed.path, settings.OAUTH.AUTHORIZE_PATH)
        self.assertEqual(actual_query, expected_query)

    def test_redirect_uri_uses_127_0_0_1_loopback_per_rfc_8252(self):
        # Setup
        expected_redirect_substring = "127.0.0.1"
        forbidden_redirect_substring = "localhost"
        # Action
        actual_url = build_authorize_url(
            api_domain="https://industrial.api.ubidots.com",
            client_id="ubidots-cli",
            state="s",
            code_challenge="c",
        )
        actual_redirect_uri = parse_qs(urlparse(actual_url).query)["redirect_uri"][0]
        # Expected
        self.assertIn(expected_redirect_substring, actual_redirect_uri)
        self.assertNotIn(forbidden_redirect_substring, actual_redirect_uri)


class TestExchangeCodeForTokens:
    @respx.mock
    def test_happy_path_returns_full_token_set(self):
        # Setup
        response_body = {
            "access_token": "jwt-access",
            "refresh_token": "opaque-refresh",
            "token_type": TokenTypeEnum.BEARER,
            "expires_in": 900,
            "scope": "read write",
        }
        respx.post("https://core.test/o/token/").mock(return_value=httpx.Response(200, json=response_body))
        # Action
        actual_tokens = exchange_code_for_tokens(
            api_domain="https://core.test",
            client_id="ubidots-cli",
            code="the-code",
            code_verifier="verifier",
        )
        # Expected
        assert actual_tokens.access_token == "jwt-access"
        assert actual_tokens.refresh_token == "opaque-refresh"
        assert actual_tokens.token_type == TokenTypeEnum.BEARER
        assert actual_tokens.scope == "read write"
        assert actual_tokens.expires_at > 0

    @respx.mock
    def test_401_response_raises_unknown_oauth_client_error(self):
        # Setup
        respx.post("https://core.test/o/token/").mock(
            return_value=httpx.Response(401, json={"error": "invalid_client"})
        )
        # Action / Expected
        with pytest.raises(UnknownOAuthClientError):
            exchange_code_for_tokens(
                api_domain="https://core.test",
                client_id="ubidots-cli",
                code="c",
                code_verifier="v",
            )

    @respx.mock
    def test_400_invalid_grant_raises_token_exchange_error_with_detail(self):
        # Setup
        respx.post("https://core.test/o/token/").mock(
            return_value=httpx.Response(
                400,
                json={"error": "invalid_grant", "error_description": "Code expired"},
            )
        )
        # Action / Expected
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
        # Action / Expected
        with pytest.raises(TokenExchangeError):
            exchange_code_for_tokens(
                api_domain="https://core.test",
                client_id="ubidots-cli",
                code="c",
                code_verifier="v",
            )

    @respx.mock
    def test_request_body_contains_pkce_verifier_and_authorization_code_grant(self):
        # Setup
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
        # Action
        exchange_code_for_tokens(
            api_domain="https://core.test",
            client_id="ubidots-cli",
            code="THECODE",
            code_verifier="THEVERIFIER",
        )
        sent_body = route.calls[0].request.content.decode("utf-8")
        actual_pairs = {k: v[0] for k, v in parse_qs(sent_body).items()}
        # Expected
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

    @pytest.mark.parametrize("status_code", [400, 401, 403, 404])
    @respx.mock
    def test_rejected_token_treated_as_already_revoked(self, status_code):
        respx.post("https://core.test/o/revoke_token/").mock(return_value=httpx.Response(status_code))
        result = revoke_refresh_token(api_domain="https://core.test", client_id="ubidots-cli", refresh_token="rt")
        assert result == RevokeResult(status="already_invalid", http_status=status_code)

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
