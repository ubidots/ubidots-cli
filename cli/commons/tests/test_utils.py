from unittest import TestCase
from unittest.mock import patch

import pytest
import typer

from cli.commons.endpoint import build_endpoint
from cli.commons.exceptions import RefreshLockTimeoutError
from cli.commons.exceptions import RefreshTokenInvalidGrantError
from cli.commons.exceptions import RefreshTokenNetworkError
from cli.config.enums import AuthHeaderTypeEnum
from cli.config.models import ProfileConfigModel

_API_DOMAIN = "https://core.example.com"
_CLIENT_ID = "ubidots-cli"


def _make_token_profile() -> ProfileConfigModel:
    return ProfileConfigModel.model_validate(
        {
            "auth_method": AuthHeaderTypeEnum.TOKEN,
            "access_token": "tok-abc",
            "api_domain": _API_DOMAIN,
        }
    )


class TestBuildEndpoint(TestCase):
    @patch("cli.commons.endpoint._get_active_profile_name", return_value="default")
    @patch("cli.commons.endpoint.ensure_fresh_token")
    def test_returns_absolute_url_and_auth_headers_for_token_profile(self, mock_refresh, _mock_profile):
        config = _make_token_profile()
        mock_refresh.return_value = config
        url, headers = build_endpoint("/api/v1.6/devices/", config)
        self.assertEqual(url, f"{_API_DOMAIN}/api/v1.6/devices/")
        self.assertIsInstance(headers, dict)

    @patch("cli.commons.endpoint._get_active_profile_name", return_value="default")
    @patch("cli.commons.endpoint.ensure_fresh_token", side_effect=RefreshTokenInvalidGrantError())
    def test_invalid_grant_error_exits_the_process(self, _mock_refresh, _mock_profile):
        with pytest.raises(typer.Exit):
            build_endpoint("/api/v1.6/devices/", _make_token_profile())

    @patch("cli.commons.endpoint._get_active_profile_name", return_value="default")
    @patch(
        "cli.commons.endpoint.ensure_fresh_token",
        side_effect=RefreshTokenNetworkError(api_domain=_API_DOMAIN),
    )
    def test_network_error_exits_the_process(self, _mock_refresh, _mock_profile):
        with pytest.raises(typer.Exit):
            build_endpoint("/api/v1.6/devices/", _make_token_profile())

    @patch("cli.commons.endpoint._get_active_profile_name", return_value="default")
    @patch("cli.commons.endpoint.ensure_fresh_token", side_effect=RefreshLockTimeoutError())
    def test_lock_timeout_exits_the_process(self, _mock_refresh, _mock_profile):
        with pytest.raises(typer.Exit):
            build_endpoint("/api/v1.6/devices/", _make_token_profile())
