import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock
from unittest.mock import patch

import filelock
import httpx
import pytest
import respx

from cli.auth.token_refresh import ensure_fresh_token
from cli.commons.exceptions import RefreshLockTimeoutError
from cli.commons.exceptions import RefreshTokenInvalidGrantError
from cli.config.enums import AuthHeaderTypeEnum
from cli.config.models import ProfileConfigModel

_API_DOMAIN = "https://core.example.com"
_TOKEN_URL = f"{_API_DOMAIN}/o/token/"
_CLIENT_ID = "ubidots-cli"
_FIXED_NOW = 1_000_000
_STALE_EXPIRES_AT = _FIXED_NOW - 3600
_FRESH_EXPIRES_AT = _FIXED_NOW + 9999


def _make_token_profile(**overrides) -> ProfileConfigModel:
    defaults: dict[str, object] = {
        "auth_method": AuthHeaderTypeEnum.TOKEN,
        "access_token": "tok-abc",
        "api_domain": _API_DOMAIN,
    }
    defaults.update(overrides)
    return ProfileConfigModel.model_validate(defaults)


def _make_oauth_profile(expires_at: int, **overrides) -> ProfileConfigModel:
    defaults: dict[str, object] = {
        "auth_method": AuthHeaderTypeEnum.OAUTH2,
        "access_token": "access-old",
        "refresh_token": "refresh-old",
        "expires_at": expires_at,
        "oauth_client_id": _CLIENT_ID,
        "api_domain": _API_DOMAIN,
        "scope": "read write",
    }
    defaults.update(overrides)
    return ProfileConfigModel.model_validate(defaults)


def _setup_mock_settings(mock_settings, tmp_path: Path, *, with_token_path: bool = True) -> None:
    mock_settings.OAUTH.REFRESH_LEEWAY_SECONDS = 30
    mock_settings.OAUTH.REFRESH_LOCK_TIMEOUT_SECONDS = 10
    mock_settings.CONFIG.PROFILES_PATH = tmp_path
    if with_token_path:
        mock_settings.OAUTH.TOKEN_PATH = "/o/token/"


class TestEnsureFreshTokenNonOAuth(TestCase):
    def test_token_profile_returned_unchanged(self):
        config = _make_token_profile()
        result = ensure_fresh_token(profile="default", config=config)
        self.assertIs(result, config)


class TestEnsureFreshTokenFreshOAuth(TestCase):
    def test_fresh_token_returned_unchanged_without_acquiring_lock(self):
        config = _make_oauth_profile(expires_at=_FRESH_EXPIRES_AT)
        with patch("cli.auth.token_refresh.filelock.FileLock") as mock_lock_cls:
            result = ensure_fresh_token(profile="default", config=config, now=lambda: _FIXED_NOW)
        self.assertIs(result, config)
        mock_lock_cls.assert_not_called()


class TestEnsureFreshTokenStaleOAuth(TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmpdir.name)

    def tearDown(self):
        self._tmpdir.cleanup()

    @respx.mock
    @patch("cli.auth.token_refresh.read_cli_configuration")
    @patch("cli.auth.token_refresh.save_profile_configuration")
    @patch("cli.auth.token_refresh.register_secret")
    def test_stale_token_is_refreshed_and_persisted(self, mock_register, mock_save, mock_read):
        config = _make_oauth_profile(expires_at=_STALE_EXPIRES_AT)
        mock_read.return_value = config
        respx.post(_TOKEN_URL).mock(
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
        with patch("cli.auth.token_refresh.settings") as mock_settings:
            _setup_mock_settings(mock_settings, self.tmp_path)
            result = ensure_fresh_token(profile="default", config=config, now=lambda: _FIXED_NOW)
        self.assertEqual(result.access_token, "new-access")
        self.assertEqual(result.refresh_token, "new-refresh")
        mock_save.assert_called_once()
        mock_register.assert_called()

    @patch("cli.auth.token_refresh.read_cli_configuration")
    @patch("cli.auth.token_refresh.save_profile_configuration")
    @patch("cli.auth.token_refresh.register_secret")
    def test_already_refreshed_by_concurrent_process_skips_network_call(self, mock_register, mock_save, mock_read):
        stale_config = _make_oauth_profile(expires_at=_STALE_EXPIRES_AT)
        fresh_config = _make_oauth_profile(expires_at=_FRESH_EXPIRES_AT)
        mock_read.return_value = fresh_config
        with patch("cli.auth.token_refresh.settings") as mock_settings:
            _setup_mock_settings(mock_settings, self.tmp_path)
            with patch("cli.auth.token_refresh.refresh_access_token") as mock_refresh:
                result = ensure_fresh_token(profile="default", config=stale_config, now=lambda: _FIXED_NOW)
        self.assertIs(result, fresh_config)
        mock_refresh.assert_not_called()
        mock_save.assert_not_called()

    @patch("cli.auth.token_refresh.read_cli_configuration")
    def test_filelock_timeout_raises_refresh_lock_timeout_error(self, mock_read):
        config = _make_oauth_profile(expires_at=_STALE_EXPIRES_AT)
        with patch("cli.auth.token_refresh.settings") as mock_settings:
            _setup_mock_settings(mock_settings, self.tmp_path, with_token_path=False)
            with patch("cli.auth.token_refresh.filelock.FileLock") as mock_lock_cls:
                mock_lock_instance = MagicMock()
                mock_lock_instance.acquire.side_effect = filelock.Timeout("lock")
                mock_lock_cls.return_value = mock_lock_instance
                with pytest.raises(RefreshLockTimeoutError):
                    ensure_fresh_token(profile="default", config=config, now=lambda: _FIXED_NOW)

    @respx.mock
    @patch("cli.auth.token_refresh.read_cli_configuration")
    @patch("cli.auth.token_refresh.save_profile_configuration")
    def test_refresh_error_propagates_without_saving(self, mock_save, mock_read):
        config = _make_oauth_profile(expires_at=_STALE_EXPIRES_AT)
        mock_read.return_value = config
        respx.post(_TOKEN_URL).mock(return_value=httpx.Response(400, json={"error": "invalid_grant"}))
        with patch("cli.auth.token_refresh.settings") as mock_settings:
            _setup_mock_settings(mock_settings, self.tmp_path)
            with pytest.raises(RefreshTokenInvalidGrantError):
                ensure_fresh_token(profile="default", config=config, now=lambda: _FIXED_NOW)
        mock_save.assert_not_called()

    @respx.mock
    @patch("cli.auth.token_refresh.read_cli_configuration")
    @patch("cli.auth.token_refresh.save_profile_configuration")
    def test_response_without_refresh_token_preserves_existing_refresh_token(self, mock_save, mock_read):
        config = _make_oauth_profile(expires_at=_STALE_EXPIRES_AT)
        mock_read.return_value = config
        respx.post(_TOKEN_URL).mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "new-access", "expires_in": 3600, "token_type": "Bearer", "scope": "read write"},
            )
        )
        with patch("cli.auth.token_refresh.settings") as mock_settings:
            _setup_mock_settings(mock_settings, self.tmp_path)
            with patch("cli.auth.token_refresh.register_secret"):
                result = ensure_fresh_token(profile="default", config=config, now=lambda: _FIXED_NOW)
        self.assertEqual(result.refresh_token, "refresh-old")
