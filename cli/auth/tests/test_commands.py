import base64
import json
import os
import pathlib
import shutil
import stat
import tempfile
import time
from datetime import datetime
from datetime import timezone
from unittest import TestCase
from unittest.mock import MagicMock
from unittest.mock import patch

import httpx
import pytest
import respx
import typer
import yaml
from typer.testing import CliRunner

from cli.auth.commands import API_DOMAIN_ENV_VAR
from cli.auth.commands import CLIENT_ID_ENV_VAR
from cli.auth.commands import LOOPBACK_PORT_ENV_VAR
from cli.auth.commands import login
from cli.auth.commands import logout
from cli.auth.commands import whoami
from cli.auth.exceptions import InvalidTokenSignatureError
from cli.auth.exceptions import JwksUnavailableError
from cli.auth.jwks_cache import JwtClaims
from cli.auth.loopback_server import LoopbackResult
from cli.auth.oauth_client import PKCEPair
from cli.auth.oauth_client import RevokeResult
from cli.auth.oauth_client import TokenSet
from cli.commons.enums import OutputFormatFieldsEnum
from cli.commons.exceptions import AuthorizationDeniedError
from cli.commons.exceptions import LoginTimeoutError
from cli.commons.exceptions import TokenExchangeError
from cli.commons.exceptions import UnknownOAuthClientError
from cli.config.models import AuthHeaderTypeEnum
from cli.settings import settings


def _jwt_with_email(email: str) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(json.dumps({"email": email}).encode()).rstrip(b"=").decode()
    return f"{header}.{payload}.sig"


_SAMPLE_JWKS = {"keys": [{"kty": "RSA", "kid": "test-key"}]}


def _login_app():
    app = typer.Typer()
    app.command()(login)
    return app


def _logout_app():
    app = typer.Typer()
    app.command()(logout)
    return app


def _whoami_app():
    app = typer.Typer()
    app.command()(whoami)
    return app


def _fake_token_set(email: str = "u@ubidots.com") -> TokenSet:
    return TokenSet(
        access_token=_jwt_with_email(email),
        refresh_token="refresh-token-fake-abcdef",
        token_type="Bearer",
        expires_at=10_000_000_000,
        scope="read write",
    )


class ProfileTestBase(TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self._tmp = tempfile.mkdtemp()
        self._tmp_path = pathlib.Path(self._tmp)
        self.profiles_dir = self._tmp_path / "profiles"
        self.profiles_dir.mkdir()
        self._orig_dir_path = settings.CONFIG.DIRECTORY_PATH
        self._orig_profiles_path = settings.CONFIG.PROFILES_PATH
        self._orig_file_path = settings.CONFIG.FILE_PATH
        settings.CONFIG.DIRECTORY_PATH = self._tmp_path
        settings.CONFIG.PROFILES_PATH = self.profiles_dir
        settings.CONFIG.FILE_PATH = self._tmp_path / "config.yaml"
        (self._tmp_path / "config.yaml").write_text(
            yaml.dump({"profilesPath": str(self.profiles_dir), "profile": "default"})
        )
        legacy_profile = {
            "api_domain": "https://core.test",
            "auth_method": AuthHeaderTypeEnum.TOKEN.value,
            "access_token": "legacy",
            "runtimes": [],
            "containerRepositoryBase": settings.CONFIG.DEFAULT_CONTAINER_REPOSITORY,
            "output_format": "machine",
        }
        legacy_path = self.profiles_dir / "default.yaml"
        legacy_path.write_text(yaml.dump(legacy_profile))
        if os.name != "nt":
            pathlib.Path(legacy_path).chmod(0o600)

    def tearDown(self):
        settings.CONFIG.DIRECTORY_PATH = self._orig_dir_path
        settings.CONFIG.PROFILES_PATH = self._orig_profiles_path
        settings.CONFIG.FILE_PATH = self._orig_file_path
        shutil.rmtree(self._tmp, ignore_errors=True)


class TestLoginHappyPath(ProfileTestBase):
    @respx.mock
    def test_login_persists_full_oauth_profile_yaml(self):
        access_jwt = _jwt_with_email("dev@ubidots.com")
        respx.post("https://core.test/o/token/").mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": access_jwt,
                    "refresh_token": "r-token",
                    "token_type": "Bearer",
                    "expires_in": 900,
                    "scope": "read write",
                },
            )
        )
        expected_yaml_keys = {
            "api_domain": "https://core.test",
            "auth_method": AuthHeaderTypeEnum.OAUTH2.value,
            "access_token": access_jwt,
            "containerRepositoryBase": settings.CONFIG.DEFAULT_CONTAINER_REPOSITORY,
            "runtimes": [],
            "output_format": OutputFormatFieldsEnum.MACHINE.value,
            "oauth_client_id": "ubidots-cli",
            "refresh_token": "r-token",
            "scope": "read write",
            "token_type": "Bearer",
        }
        with (
            patch("cli.auth.commands.port_available", return_value=True),
            patch("cli.auth.commands.webbrowser.open", return_value=True),
            patch("cli.auth.commands.LoopbackServer") as mock_server,
            patch(
                "cli.auth.commands.generate_pkce_pair",
                return_value=PKCEPair(verifier="v", challenge="c"),
            ),
            patch("cli.auth.commands.generate_state", return_value="s"),
        ):
            mock_server.return_value.wait_for_callback.return_value = LoopbackResult(code="THECODE", state="s")
            result = self.runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        actual_yaml = yaml.safe_load((self.profiles_dir / "default.yaml").read_text())
        actual_expires_at = actual_yaml.pop("expires_at")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("Login successful as dev@ubidots.com", result.output)
        self.assertEqual(actual_yaml, expected_yaml_keys)
        self.assertGreater(actual_expires_at, 0)


class TestLoginErrorPaths(ProfileTestBase):
    def test_state_mismatch_aborts_and_leaves_legacy_profile_intact(self):
        expected_yaml_after = {
            "api_domain": "https://core.test",
            "auth_method": AuthHeaderTypeEnum.TOKEN.value,
            "access_token": "legacy",
            "runtimes": [],
            "containerRepositoryBase": settings.CONFIG.DEFAULT_CONTAINER_REPOSITORY,
            "output_format": OutputFormatFieldsEnum.MACHINE.value,
        }
        with (
            patch("cli.auth.commands.port_available", return_value=True),
            patch("cli.auth.commands.webbrowser.open", return_value=True),
            patch("cli.auth.commands.LoopbackServer") as mock_server,
            patch(
                "cli.auth.commands.generate_pkce_pair",
                return_value=PKCEPair(verifier="v", challenge="c"),
            ),
            patch("cli.auth.commands.generate_state", return_value="expected"),
        ):
            mock_server.return_value.wait_for_callback.return_value = LoopbackResult(code="code", state="evil")
            result = self.runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        actual_yaml = yaml.safe_load((self.profiles_dir / "default.yaml").read_text())
        self.assertEqual(result.exit_code, 4)
        self.assertIn("CSRF mismatch", result.output)
        self.assertEqual(actual_yaml, expected_yaml_after)

    def test_no_browser_prints_authorize_url_without_opening_browser(self):
        with (
            patch("cli.auth.commands.port_available", return_value=True),
            patch("cli.auth.commands.webbrowser.open") as opener,
            patch("cli.auth.commands.LoopbackServer") as mock_server,
            patch(
                "cli.auth.commands.generate_pkce_pair",
                return_value=PKCEPair(verifier="v", challenge="c"),
            ),
            patch("cli.auth.commands.generate_state", return_value="s"),
            patch(
                "cli.auth.commands.exchange_code_for_tokens",
                return_value=_fake_token_set(),
            ),
        ):
            mock_server.return_value.wait_for_callback.return_value = LoopbackResult(code="code", state="s")
            result = self.runner.invoke(_login_app(), ["--client-id", "ubidots-cli", "--no-browser"])
        self.assertEqual(result.exit_code, 0)
        opener.assert_not_called()
        self.assertIn("/o/authorize/", result.output)


class TestLoginFilePermissions(ProfileTestBase):
    @pytest.mark.skipif(os.name == "nt", reason="POSIX-only")
    def test_login_writes_profile_with_mode_0600(self):
        expected_mode = 0o600
        with (
            patch("cli.auth.commands.port_available", return_value=True),
            patch("cli.auth.commands.webbrowser.open", return_value=True),
            patch("cli.auth.commands.LoopbackServer") as mock_server,
            patch(
                "cli.auth.commands.generate_pkce_pair",
                return_value=PKCEPair(verifier="v", challenge="c"),
            ),
            patch("cli.auth.commands.generate_state", return_value="s"),
            patch(
                "cli.auth.commands.exchange_code_for_tokens",
                return_value=_fake_token_set(),
            ),
        ):
            mock_server.return_value.wait_for_callback.return_value = LoopbackResult(code="code", state="s")
            self.runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        actual_mode = stat.S_IMODE((self.profiles_dir / "default.yaml").stat().st_mode)
        self.assertEqual(actual_mode, expected_mode)


class TestClientIdResolution(ProfileTestBase):
    def test_no_client_id_anywhere_exits_with_hint(self):
        orig_env = os.environ.pop(CLIENT_ID_ENV_VAR, None)
        orig_client_id = settings.OAUTH.DEFAULT_CLIENT_ID
        settings.OAUTH.DEFAULT_CLIENT_ID = ""
        try:
            with patch("cli.auth.commands.port_available", return_value=True):
                result = self.runner.invoke(_login_app(), [])
            self.assertEqual(result.exit_code, 64)
            self.assertIn(CLIENT_ID_ENV_VAR, result.output)
        finally:
            if orig_env is not None:
                os.environ[CLIENT_ID_ENV_VAR] = orig_env
            settings.OAUTH.DEFAULT_CLIENT_ID = orig_client_id

    def test_env_var_supplies_client_id_when_flag_and_settings_absent(self):
        orig_env = os.environ.get(CLIENT_ID_ENV_VAR)
        os.environ[CLIENT_ID_ENV_VAR] = "from-env"
        orig_client_id = settings.OAUTH.DEFAULT_CLIENT_ID
        settings.OAUTH.DEFAULT_CLIENT_ID = ""
        try:
            with (
                patch("cli.auth.commands.port_available", return_value=True),
                patch("cli.auth.commands.webbrowser.open", return_value=True),
                patch("cli.auth.commands.LoopbackServer") as mock_server,
                patch(
                    "cli.auth.commands.generate_pkce_pair",
                    return_value=PKCEPair(verifier="v", challenge="c"),
                ),
                patch("cli.auth.commands.generate_state", return_value="s"),
                patch(
                    "cli.auth.commands.exchange_code_for_tokens",
                    return_value=_fake_token_set(),
                ) as mock_exchange,
            ):
                mock_server.return_value.wait_for_callback.return_value = LoopbackResult(code="code", state="s")
                result = self.runner.invoke(_login_app(), [])
            saved_yaml = yaml.safe_load((self.profiles_dir / "default.yaml").read_text())
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(mock_exchange.call_args.kwargs["client_id"], "from-env")
            self.assertEqual(saved_yaml["oauth_client_id"], "from-env")
        finally:
            if orig_env is not None:
                os.environ[CLIENT_ID_ENV_VAR] = orig_env
            else:
                os.environ.pop(CLIENT_ID_ENV_VAR, None)
            settings.OAUTH.DEFAULT_CLIENT_ID = orig_client_id

    def test_flag_overrides_env_and_settings(self):
        orig_env = os.environ.get(CLIENT_ID_ENV_VAR)
        os.environ[CLIENT_ID_ENV_VAR] = "from-env"
        orig_client_id = settings.OAUTH.DEFAULT_CLIENT_ID
        settings.OAUTH.DEFAULT_CLIENT_ID = "from-settings"
        try:
            with (
                patch("cli.auth.commands.port_available", return_value=True),
                patch("cli.auth.commands.webbrowser.open", return_value=True),
                patch("cli.auth.commands.LoopbackServer") as mock_server,
                patch(
                    "cli.auth.commands.generate_pkce_pair",
                    return_value=PKCEPair(verifier="v", challenge="c"),
                ),
                patch("cli.auth.commands.generate_state", return_value="s"),
                patch(
                    "cli.auth.commands.exchange_code_for_tokens",
                    return_value=_fake_token_set(),
                ) as mock_exchange,
            ):
                mock_server.return_value.wait_for_callback.return_value = LoopbackResult(code="code", state="s")
                result = self.runner.invoke(_login_app(), ["--client-id", "from-flag"])
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(mock_exchange.call_args.kwargs["client_id"], "from-flag")
        finally:
            if orig_env is not None:
                os.environ[CLIENT_ID_ENV_VAR] = orig_env
            else:
                os.environ.pop(CLIENT_ID_ENV_VAR, None)
            settings.OAUTH.DEFAULT_CLIENT_ID = orig_client_id

    def test_settings_default_is_used_when_no_flag_and_no_env(self):
        orig_env = os.environ.pop(CLIENT_ID_ENV_VAR, None)
        orig_client_id = settings.OAUTH.DEFAULT_CLIENT_ID
        settings.OAUTH.DEFAULT_CLIENT_ID = "ubidots-cli"
        try:
            with (
                patch("cli.auth.commands.port_available", return_value=True),
                patch("cli.auth.commands.webbrowser.open", return_value=True),
                patch("cli.auth.commands.LoopbackServer") as mock_server,
                patch(
                    "cli.auth.commands.generate_pkce_pair",
                    return_value=PKCEPair(verifier="v", challenge="c"),
                ),
                patch("cli.auth.commands.generate_state", return_value="s"),
                patch(
                    "cli.auth.commands.exchange_code_for_tokens",
                    return_value=_fake_token_set(),
                ) as mock_exchange,
            ):
                mock_server.return_value.wait_for_callback.return_value = LoopbackResult(code="code", state="s")
                result = self.runner.invoke(_login_app(), [])
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(mock_exchange.call_args.kwargs["client_id"], "ubidots-cli")
        finally:
            if orig_env is not None:
                os.environ[CLIENT_ID_ENV_VAR] = orig_env
            settings.OAUTH.DEFAULT_CLIENT_ID = orig_client_id

    def test_profile_oauth_client_id_used_when_no_flag_no_env(self):
        orig_env = os.environ.pop(CLIENT_ID_ENV_VAR, None)
        orig_client_id = settings.OAUTH.DEFAULT_CLIENT_ID
        settings.OAUTH.DEFAULT_CLIENT_ID = ""
        profile_with_client = {
            "api_domain": "https://core.test",
            "auth_method": AuthHeaderTypeEnum.TOKEN.value,
            "access_token": "tok",
            "oauth_client_id": "from-profile",
            "runtimes": [],
            "containerRepositoryBase": settings.CONFIG.DEFAULT_CONTAINER_REPOSITORY,
            "output_format": "machine",
        }
        profile_file = self.profiles_dir / "default.yaml"
        profile_file.write_text(yaml.dump(profile_with_client))
        if os.name != "nt":
            pathlib.Path(profile_file).chmod(0o600)
        try:
            with (
                patch("cli.auth.commands.port_available", return_value=True),
                patch("cli.auth.commands.webbrowser.open", return_value=True),
                patch("cli.auth.commands.LoopbackServer") as mock_server,
                patch(
                    "cli.auth.commands.generate_pkce_pair",
                    return_value=PKCEPair(verifier="v", challenge="c"),
                ),
                patch("cli.auth.commands.generate_state", return_value="s"),
                patch(
                    "cli.auth.commands.exchange_code_for_tokens",
                    return_value=_fake_token_set(),
                ) as mock_exchange,
            ):
                mock_server.return_value.wait_for_callback.return_value = LoopbackResult(code="code", state="s")
                result = self.runner.invoke(_login_app(), [])
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(mock_exchange.call_args.kwargs["client_id"], "from-profile")
        finally:
            if orig_env is not None:
                os.environ[CLIENT_ID_ENV_VAR] = orig_env
            settings.OAUTH.DEFAULT_CLIENT_ID = orig_client_id


class TestPortResolution(ProfileTestBase):
    def test_default_port_is_53682_when_no_flag_no_env(self):
        orig_env = os.environ.pop(LOOPBACK_PORT_ENV_VAR, None)
        try:
            with (
                patch("cli.auth.commands.port_available", return_value=True) as mock_port_check,
                patch("cli.auth.commands.webbrowser.open", return_value=True),
                patch("cli.auth.commands.LoopbackServer") as mock_server,
                patch(
                    "cli.auth.commands.generate_pkce_pair",
                    return_value=PKCEPair(verifier="v", challenge="c"),
                ),
                patch("cli.auth.commands.generate_state", return_value="s"),
                patch(
                    "cli.auth.commands.exchange_code_for_tokens",
                    return_value=_fake_token_set(),
                ) as mock_exchange,
            ):
                mock_server.return_value.wait_for_callback.return_value = LoopbackResult(code="code", state="s")
                self.runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
            self.assertEqual(mock_port_check.call_args.kwargs, {"port": 53682})
            mock_server.assert_called_once_with(port=53682)
            self.assertEqual(mock_exchange.call_args.kwargs["redirect_uri"], "http://127.0.0.1:53682/callback")
        finally:
            if orig_env is not None:
                os.environ[LOOPBACK_PORT_ENV_VAR] = orig_env

    def test_flag_overrides_default_port_in_redirect_uri_and_server(self):
        orig_env = os.environ.pop(LOOPBACK_PORT_ENV_VAR, None)
        try:
            with (
                patch("cli.auth.commands.port_available", return_value=True) as mock_port_check,
                patch("cli.auth.commands.webbrowser.open", return_value=True),
                patch("cli.auth.commands.LoopbackServer") as mock_server,
                patch(
                    "cli.auth.commands.generate_pkce_pair",
                    return_value=PKCEPair(verifier="v", challenge="c"),
                ),
                patch("cli.auth.commands.generate_state", return_value="s"),
                patch(
                    "cli.auth.commands.exchange_code_for_tokens",
                    return_value=_fake_token_set(),
                ) as mock_exchange,
            ):
                mock_server.return_value.wait_for_callback.return_value = LoopbackResult(code="code", state="s")
                result = self.runner.invoke(_login_app(), ["--client-id", "ubidots-cli", "--port", "65000"])
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(mock_port_check.call_args.kwargs, {"port": 65000})
            mock_server.assert_called_once_with(port=65000)
            self.assertEqual(mock_exchange.call_args.kwargs["redirect_uri"], "http://127.0.0.1:65000/callback")
        finally:
            if orig_env is not None:
                os.environ[LOOPBACK_PORT_ENV_VAR] = orig_env

    def test_env_var_supplies_port_when_flag_absent(self):
        orig_env = os.environ.get(LOOPBACK_PORT_ENV_VAR)
        os.environ[LOOPBACK_PORT_ENV_VAR] = "60000"
        try:
            with (
                patch("cli.auth.commands.port_available", return_value=True) as mock_port_check,
                patch("cli.auth.commands.webbrowser.open", return_value=True),
                patch("cli.auth.commands.LoopbackServer") as mock_server,
                patch(
                    "cli.auth.commands.generate_pkce_pair",
                    return_value=PKCEPair(verifier="v", challenge="c"),
                ),
                patch("cli.auth.commands.generate_state", return_value="s"),
                patch(
                    "cli.auth.commands.exchange_code_for_tokens",
                    return_value=_fake_token_set(),
                ),
            ):
                mock_server.return_value.wait_for_callback.return_value = LoopbackResult(code="code", state="s")
                result = self.runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(mock_port_check.call_args.kwargs, {"port": 60000})
            mock_server.assert_called_once_with(port=60000)
        finally:
            if orig_env is not None:
                os.environ[LOOPBACK_PORT_ENV_VAR] = orig_env
            else:
                os.environ.pop(LOOPBACK_PORT_ENV_VAR, None)

    def test_port_in_use_message_lists_diagnostic_commands(self):
        orig_env = os.environ.pop(LOOPBACK_PORT_ENV_VAR, None)
        try:
            with patch("cli.auth.commands.port_available", return_value=False):
                result = self.runner.invoke(_login_app(), ["--client-id", "ubidots-cli", "--port", "53682"])
            self.assertEqual(result.exit_code, 64)
            self.assertIn("lsof", result.output)
            self.assertIn("--port", result.output)
            self.assertIn(LOOPBACK_PORT_ENV_VAR, result.output)
        finally:
            if orig_env is not None:
                os.environ[LOOPBACK_PORT_ENV_VAR] = orig_env


class TestApiDomainResolution(ProfileTestBase):
    def test_flag_overrides_profile_api_domain_and_is_persisted(self):
        orig_env = os.environ.pop(API_DOMAIN_ENV_VAR, None)
        try:
            with (
                patch("cli.auth.commands.port_available", return_value=True),
                patch("cli.auth.commands.webbrowser.open", return_value=True),
                patch("cli.auth.commands.LoopbackServer") as mock_server,
                patch(
                    "cli.auth.commands.generate_pkce_pair",
                    return_value=PKCEPair(verifier="v", challenge="c"),
                ),
                patch("cli.auth.commands.generate_state", return_value="s"),
                patch(
                    "cli.auth.commands.exchange_code_for_tokens",
                    return_value=_fake_token_set(),
                ) as mock_exchange,
            ):
                mock_server.return_value.wait_for_callback.return_value = LoopbackResult(code="code", state="s")
                result = self.runner.invoke(
                    _login_app(),
                    ["--client-id", "ubidots-cli", "--api-domain", "https://cs.ubidots.site"],
                )
            saved_yaml = yaml.safe_load((self.profiles_dir / "default.yaml").read_text())
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(mock_exchange.call_args.kwargs["api_domain"], "https://cs.ubidots.site")
            self.assertEqual(saved_yaml["api_domain"], "https://cs.ubidots.site")
        finally:
            if orig_env is not None:
                os.environ[API_DOMAIN_ENV_VAR] = orig_env

    def test_env_var_supplies_api_domain_when_flag_absent(self):
        orig_env = os.environ.get(API_DOMAIN_ENV_VAR)
        os.environ[API_DOMAIN_ENV_VAR] = "https://cs.ubidots.site"
        try:
            with (
                patch("cli.auth.commands.port_available", return_value=True),
                patch("cli.auth.commands.webbrowser.open", return_value=True),
                patch("cli.auth.commands.LoopbackServer") as mock_server,
                patch(
                    "cli.auth.commands.generate_pkce_pair",
                    return_value=PKCEPair(verifier="v", challenge="c"),
                ),
                patch("cli.auth.commands.generate_state", return_value="s"),
                patch(
                    "cli.auth.commands.exchange_code_for_tokens",
                    return_value=_fake_token_set(),
                ) as mock_exchange,
            ):
                mock_server.return_value.wait_for_callback.return_value = LoopbackResult(code="code", state="s")
                result = self.runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(mock_exchange.call_args.kwargs["api_domain"], "https://cs.ubidots.site")
        finally:
            if orig_env is not None:
                os.environ[API_DOMAIN_ENV_VAR] = orig_env
            else:
                os.environ.pop(API_DOMAIN_ENV_VAR, None)

    def test_profile_api_domain_used_when_no_flag_no_env(self):
        orig_env = os.environ.pop(API_DOMAIN_ENV_VAR, None)
        try:
            with (
                patch("cli.auth.commands.port_available", return_value=True),
                patch("cli.auth.commands.webbrowser.open", return_value=True),
                patch("cli.auth.commands.LoopbackServer") as mock_server,
                patch(
                    "cli.auth.commands.generate_pkce_pair",
                    return_value=PKCEPair(verifier="v", challenge="c"),
                ),
                patch("cli.auth.commands.generate_state", return_value="s"),
                patch(
                    "cli.auth.commands.exchange_code_for_tokens",
                    return_value=_fake_token_set(),
                ) as mock_exchange,
            ):
                mock_server.return_value.wait_for_callback.return_value = LoopbackResult(code="code", state="s")
                result = self.runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(mock_exchange.call_args.kwargs["api_domain"], "https://core.test")
        finally:
            if orig_env is not None:
                os.environ[API_DOMAIN_ENV_VAR] = orig_env


class TestProfileResolution(ProfileTestBase):
    def test_no_profile_flag_writes_to_active_profile_not_default(self):
        (self.profiles_dir / "default.yaml").unlink()
        (self._tmp_path / "config.yaml").write_text(
            yaml.dump({"profilesPath": str(self.profiles_dir), "profile": "staging"})
        )
        staging_profile = {
            "api_domain": "https://staging.test",
            "auth_method": AuthHeaderTypeEnum.TOKEN.value,
            "access_token": "legacy-staging",
            "runtimes": [],
            "containerRepositoryBase": settings.CONFIG.DEFAULT_CONTAINER_REPOSITORY,
            "output_format": "machine",
        }
        staging_path = self.profiles_dir / "staging.yaml"
        staging_path.write_text(yaml.dump(staging_profile))
        if os.name != "nt":
            pathlib.Path(staging_path).chmod(0o600)
        with (
            patch("cli.auth.commands.port_available", return_value=True),
            patch("cli.auth.commands.webbrowser.open", return_value=True),
            patch("cli.auth.commands.LoopbackServer") as mock_server,
            patch(
                "cli.auth.commands.generate_pkce_pair",
                return_value=PKCEPair(verifier="v", challenge="c"),
            ),
            patch("cli.auth.commands.generate_state", return_value="s"),
            patch(
                "cli.auth.commands.exchange_code_for_tokens",
                return_value=_fake_token_set(),
            ),
        ):
            mock_server.return_value.wait_for_callback.return_value = LoopbackResult(code="code", state="s")
            result = self.runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("profile 'staging'", result.output)
        saved = yaml.safe_load(staging_path.read_text())
        self.assertEqual(saved["auth_method"], AuthHeaderTypeEnum.OAUTH2.value)
        self.assertTrue(saved["refresh_token"])
        self.assertFalse((self.profiles_dir / "default.yaml").exists())

    def test_explicit_profile_flag_creates_new_profile_if_missing(self):
        new_profile_path = self.profiles_dir / "fresh.yaml"
        self.assertFalse(new_profile_path.exists())
        with (
            patch("cli.auth.commands.port_available", return_value=True),
            patch("cli.auth.commands.webbrowser.open", return_value=True),
            patch("cli.auth.commands.LoopbackServer") as mock_server,
            patch(
                "cli.auth.commands.generate_pkce_pair",
                return_value=PKCEPair(verifier="v", challenge="c"),
            ),
            patch("cli.auth.commands.generate_state", return_value="s"),
            patch(
                "cli.auth.commands.exchange_code_for_tokens",
                return_value=_fake_token_set(),
            ),
        ):
            mock_server.return_value.wait_for_callback.return_value = LoopbackResult(code="code", state="s")
            result = self.runner.invoke(
                _login_app(),
                ["--client-id", "ubidots-cli", "--profile", "fresh"],
            )
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("does not exist yet", result.output)
        self.assertTrue(new_profile_path.exists())
        saved = yaml.safe_load(new_profile_path.read_text())
        self.assertEqual(saved["auth_method"], AuthHeaderTypeEnum.OAUTH2.value)

    def test_explicit_profile_flag_only_touches_target_profile(self):
        default_before = (self.profiles_dir / "default.yaml").read_text()
        with (
            patch("cli.auth.commands.port_available", return_value=True),
            patch("cli.auth.commands.webbrowser.open", return_value=True),
            patch("cli.auth.commands.LoopbackServer") as mock_server,
            patch(
                "cli.auth.commands.generate_pkce_pair",
                return_value=PKCEPair(verifier="v", challenge="c"),
            ),
            patch("cli.auth.commands.generate_state", return_value="s"),
            patch(
                "cli.auth.commands.exchange_code_for_tokens",
                return_value=_fake_token_set(),
            ),
        ):
            mock_server.return_value.wait_for_callback.return_value = LoopbackResult(code="code", state="s")
            result = self.runner.invoke(
                _login_app(),
                ["--client-id", "ubidots-cli", "--profile", "other"],
            )
        default_after = (self.profiles_dir / "default.yaml").read_text()
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(default_before, default_after)


class TestActiveSessionConfirmation(ProfileTestBase):
    def _seed_oauth_profile(self, profile_name="default"):
        profile_data = {
            "api_domain": "https://core.test",
            "auth_method": AuthHeaderTypeEnum.OAUTH2.value,
            "access_token": _jwt_with_email("existing@ubidots.com"),
            "refresh_token": "old-refresh",
            "expires_at": 10_000_000_000,
            "oauth_client_id": "ubidots-cli",
            "scope": "read write",
            "token_type": "Bearer",
            "runtimes": [],
            "containerRepositoryBase": settings.CONFIG.DEFAULT_CONTAINER_REPOSITORY,
            "output_format": "machine",
        }
        profile_path = self.profiles_dir / f"{profile_name}.yaml"
        profile_path.write_text(yaml.dump(profile_data))
        if os.name != "nt":
            pathlib.Path(profile_path).chmod(0o600)

    def test_active_oauth_session_prompts_for_confirmation_and_aborts_on_no(self):
        self._seed_oauth_profile()
        with (
            patch("cli.auth.commands.port_available", return_value=True),
            patch("cli.auth.commands.LoopbackServer"),
        ):
            result = self.runner.invoke(_login_app(), ["--client-id", "ubidots-cli"], input="n\n")
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("already has an active OAuth session", result.output)
        self.assertIn("existing@ubidots.com", result.output)
        self.assertIn("Aborted by user", result.output)

    def test_yes_flag_skips_confirmation_prompt(self):
        self._seed_oauth_profile()
        with (
            patch("cli.auth.commands.port_available", return_value=True),
            patch("cli.auth.commands.webbrowser.open", return_value=True),
            patch("cli.auth.commands.LoopbackServer") as mock_server,
            patch(
                "cli.auth.commands.generate_pkce_pair",
                return_value=PKCEPair(verifier="v", challenge="c"),
            ),
            patch("cli.auth.commands.generate_state", return_value="s"),
            patch(
                "cli.auth.commands.exchange_code_for_tokens",
                return_value=_fake_token_set("new@ubidots.com"),
            ),
        ):
            mock_server.return_value.wait_for_callback.return_value = LoopbackResult(code="code", state="s")
            result = self.runner.invoke(_login_app(), ["--client-id", "ubidots-cli", "--yes"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("new@ubidots.com", result.output)

    def test_short_y_flag_skips_confirmation_prompt(self):
        self._seed_oauth_profile()
        with (
            patch("cli.auth.commands.port_available", return_value=True),
            patch("cli.auth.commands.webbrowser.open", return_value=True),
            patch("cli.auth.commands.LoopbackServer") as mock_server,
            patch(
                "cli.auth.commands.generate_pkce_pair",
                return_value=PKCEPair(verifier="v", challenge="c"),
            ),
            patch("cli.auth.commands.generate_state", return_value="s"),
            patch(
                "cli.auth.commands.exchange_code_for_tokens",
                return_value=_fake_token_set("new@ubidots.com"),
            ),
        ):
            mock_server.return_value.wait_for_callback.return_value = LoopbackResult(code="code", state="s")
            result = self.runner.invoke(_login_app(), ["--client-id", "ubidots-cli", "-y"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertNotIn("Overwrite", result.output)
        self.assertIn("new@ubidots.com", result.output)

    def test_login_help_lists_short_y_and_long_yes_flags(self):
        result = self.runner.invoke(_login_app(), ["--help"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("--yes", result.output)
        self.assertIn("-y", result.output)


class TestErrorPaths(ProfileTestBase):
    def test_authorization_denied_exits_with_code_2(self):
        with (
            patch("cli.auth.commands.port_available", return_value=True),
            patch("cli.auth.commands.LoopbackServer") as mock_server,
            patch(
                "cli.auth.commands.generate_pkce_pair",
                return_value=PKCEPair(verifier="v", challenge="c"),
            ),
            patch("cli.auth.commands.generate_state", return_value="s"),
        ):
            mock_server.return_value.wait_for_callback.side_effect = AuthorizationDeniedError()
            result = self.runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        self.assertEqual(result.exit_code, 2)
        self.assertIn("Authorization denied", result.output)

    def test_login_timeout_exits_with_code_3(self):
        with (
            patch("cli.auth.commands.port_available", return_value=True),
            patch("cli.auth.commands.LoopbackServer") as mock_server,
            patch(
                "cli.auth.commands.generate_pkce_pair",
                return_value=PKCEPair(verifier="v", challenge="c"),
            ),
            patch("cli.auth.commands.generate_state", return_value="s"),
        ):
            mock_server.return_value.wait_for_callback.side_effect = LoginTimeoutError()
            result = self.runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        self.assertEqual(result.exit_code, 3)
        self.assertIn("timed out", result.output.lower())

    def test_unknown_oauth_client_exits_with_code_5(self):
        with (
            patch("cli.auth.commands.port_available", return_value=True),
            patch("cli.auth.commands.LoopbackServer") as mock_server,
            patch(
                "cli.auth.commands.generate_pkce_pair",
                return_value=PKCEPair(verifier="v", challenge="c"),
            ),
            patch("cli.auth.commands.generate_state", return_value="s"),
            patch(
                "cli.auth.commands.exchange_code_for_tokens",
                side_effect=UnknownOAuthClientError(),
            ),
        ):
            mock_server.return_value.wait_for_callback.return_value = LoopbackResult(code="code", state="s")
            result = self.runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        self.assertEqual(result.exit_code, 5)
        self.assertIn("Unknown OAuth client", result.output)

    def test_token_exchange_failure_exits_with_code_5(self):
        with (
            patch("cli.auth.commands.port_available", return_value=True),
            patch("cli.auth.commands.LoopbackServer") as mock_server,
            patch(
                "cli.auth.commands.generate_pkce_pair",
                return_value=PKCEPair(verifier="v", challenge="c"),
            ),
            patch("cli.auth.commands.generate_state", return_value="s"),
            patch(
                "cli.auth.commands.exchange_code_for_tokens",
                side_effect=TokenExchangeError(detail="server error"),
            ),
        ):
            mock_server.return_value.wait_for_callback.return_value = LoopbackResult(code="code", state="s")
            result = self.runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        self.assertEqual(result.exit_code, 5)


class TestRedactionAndVerbose(ProfileTestBase):
    def test_verbose_prints_redirect_uri_and_authorize_url(self):
        with (
            patch("cli.auth.commands.port_available", return_value=True),
            patch("cli.auth.commands.LoopbackServer") as mock_server,
            patch(
                "cli.auth.commands.generate_pkce_pair",
                return_value=PKCEPair(verifier="v", challenge="c"),
            ),
            patch("cli.auth.commands.generate_state", return_value="s"),
            patch(
                "cli.auth.commands.exchange_code_for_tokens",
                return_value=_fake_token_set(),
            ),
        ):
            mock_server.return_value.wait_for_callback.return_value = LoopbackResult(code="code", state="s")
            result = self.runner.invoke(
                _login_app(),
                ["--client-id", "ubidots-cli", "--no-browser", "--verbose"],
            )
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("redirect_uri:", result.output)
        self.assertIn("/o/authorize/", result.output)

    def test_verifier_never_appears_in_output(self):
        long_verifier = "V" * 64
        with (
            patch("cli.auth.commands.port_available", return_value=True),
            patch("cli.auth.commands.webbrowser.open", return_value=True),
            patch("cli.auth.commands.LoopbackServer") as mock_server,
            patch(
                "cli.auth.commands.generate_pkce_pair",
                return_value=PKCEPair(verifier=long_verifier, challenge="fakechal"),
            ),
            patch("cli.auth.commands.generate_state", return_value="s"),
            patch(
                "cli.auth.commands.exchange_code_for_tokens",
                return_value=_fake_token_set(),
            ),
        ):
            mock_server.return_value.wait_for_callback.return_value = LoopbackResult(code="code", state="s")
            result = self.runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertNotIn(long_verifier, result.output)

    def test_authorization_code_never_appears_in_output(self):
        distinctive_code = "AUTHCODEABCDEF123456"
        with (
            patch("cli.auth.commands.port_available", return_value=True),
            patch("cli.auth.commands.webbrowser.open", return_value=True),
            patch("cli.auth.commands.LoopbackServer") as mock_server,
            patch(
                "cli.auth.commands.generate_pkce_pair",
                return_value=PKCEPair(verifier="v" * 64, challenge="fakechal"),
            ),
            patch("cli.auth.commands.generate_state", return_value="s"),
            patch(
                "cli.auth.commands.exchange_code_for_tokens",
                return_value=_fake_token_set(),
            ),
        ):
            mock_server.return_value.wait_for_callback.return_value = LoopbackResult(code=distinctive_code, state="s")
            result = self.runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertNotIn(distinctive_code, result.output)

    def test_access_and_refresh_tokens_not_in_output(self):
        token_set = _fake_token_set("clean@ubidots.com")
        with (
            patch("cli.auth.commands.port_available", return_value=True),
            patch("cli.auth.commands.webbrowser.open", return_value=True),
            patch("cli.auth.commands.LoopbackServer") as mock_server,
            patch(
                "cli.auth.commands.generate_pkce_pair",
                return_value=PKCEPair(verifier="v", challenge="c"),
            ),
            patch("cli.auth.commands.generate_state", return_value="s"),
            patch(
                "cli.auth.commands.exchange_code_for_tokens",
                return_value=token_set,
            ),
        ):
            mock_server.return_value.wait_for_callback.return_value = LoopbackResult(code="code", state="s")
            result = self.runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertNotIn(token_set.access_token, result.output)
        self.assertNotIn(token_set.refresh_token, result.output)

    def test_default_scope_in_authorize_url(self):
        with (
            patch("cli.auth.commands.port_available", return_value=True),
            patch("cli.auth.commands.LoopbackServer") as mock_server,
            patch(
                "cli.auth.commands.generate_pkce_pair",
                return_value=PKCEPair(verifier="v", challenge="c"),
            ),
            patch("cli.auth.commands.generate_state", return_value="s"),
            patch(
                "cli.auth.commands.exchange_code_for_tokens",
                return_value=_fake_token_set(),
            ),
        ):
            mock_server.return_value.wait_for_callback.return_value = LoopbackResult(code="code", state="s")
            result = self.runner.invoke(_login_app(), ["--client-id", "ubidots-cli", "--no-browser"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("read", result.output)
        self.assertIn("write", result.output)
        self.assertIn("offline_access", result.output)

    def test_custom_scope_flag_in_authorize_url(self):
        with (
            patch("cli.auth.commands.port_available", return_value=True),
            patch("cli.auth.commands.LoopbackServer") as mock_server,
            patch(
                "cli.auth.commands.generate_pkce_pair",
                return_value=PKCEPair(verifier="v", challenge="c"),
            ),
            patch("cli.auth.commands.generate_state", return_value="s"),
            patch(
                "cli.auth.commands.exchange_code_for_tokens",
                return_value=_fake_token_set(),
            ),
        ):
            mock_server.return_value.wait_for_callback.return_value = LoopbackResult(code="code", state="s")
            result = self.runner.invoke(
                _login_app(),
                ["--client-id", "ubidots-cli", "--no-browser", "--scope", "read:data"],
            )
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertTrue("read%3Adata" in result.output or "read:data" in result.output)


class TestBrowserAndServerEdgeCases(ProfileTestBase):
    def test_browser_open_fails_prints_fallback_url(self):
        with (
            patch("cli.auth.commands.port_available", return_value=True),
            patch("cli.auth.commands.webbrowser.open", return_value=False),
            patch("cli.auth.commands.LoopbackServer") as mock_server,
            patch(
                "cli.auth.commands.generate_pkce_pair",
                return_value=PKCEPair(verifier="v", challenge="c"),
            ),
            patch("cli.auth.commands.generate_state", return_value="s"),
            patch(
                "cli.auth.commands.exchange_code_for_tokens",
                return_value=_fake_token_set(),
            ),
        ):
            mock_server.return_value.wait_for_callback.return_value = LoopbackResult(code="code", state="s")
            result = self.runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("/o/authorize/", result.output)

    def test_loopback_server_oserror_exits_with_code_64(self):
        with (
            patch("cli.auth.commands.port_available", return_value=True),
            patch(
                "cli.auth.commands.LoopbackServer",
                side_effect=OSError("address in use"),
            ),
            patch(
                "cli.auth.commands.generate_pkce_pair",
                return_value=PKCEPair(verifier="v", challenge="c"),
            ),
            patch("cli.auth.commands.generate_state", return_value="s"),
        ):
            result = self.runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        self.assertEqual(result.exit_code, 64)

    def test_custom_timeout_passed_to_wait_for_callback(self):
        with (
            patch("cli.auth.commands.port_available", return_value=True),
            patch("cli.auth.commands.webbrowser.open", return_value=True),
            patch("cli.auth.commands.LoopbackServer") as mock_server,
            patch(
                "cli.auth.commands.generate_pkce_pair",
                return_value=PKCEPair(verifier="v", challenge="c"),
            ),
            patch("cli.auth.commands.generate_state", return_value="s"),
            patch(
                "cli.auth.commands.exchange_code_for_tokens",
                return_value=_fake_token_set(),
            ),
        ):
            mock_server.return_value.wait_for_callback.return_value = LoopbackResult(code="code", state="s")
            result = self.runner.invoke(_login_app(), ["--client-id", "ubidots-cli", "--timeout", "42"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(mock_server.return_value.wait_for_callback.call_args.kwargs["timeout"], 42)


class TestActiveSessionExpiry(ProfileTestBase):
    def test_expired_oauth_session_does_not_prompt_for_confirmation(self):
        expired_profile = {
            "api_domain": "https://core.test",
            "auth_method": AuthHeaderTypeEnum.OAUTH2.value,
            "access_token": _jwt_with_email("old@ubidots.com"),
            "refresh_token": "old-refresh",
            "expires_at": 1,
            "oauth_client_id": "ubidots-cli",
            "scope": "read write",
            "token_type": "Bearer",
            "runtimes": [],
            "containerRepositoryBase": settings.CONFIG.DEFAULT_CONTAINER_REPOSITORY,
            "output_format": "machine",
        }
        (self.profiles_dir / "default.yaml").write_text(yaml.dump(expired_profile))
        with (
            patch("cli.auth.commands.port_available", return_value=True),
            patch("cli.auth.commands.webbrowser.open", return_value=True),
            patch("cli.auth.commands.LoopbackServer") as mock_server,
            patch(
                "cli.auth.commands.generate_pkce_pair",
                return_value=PKCEPair(verifier="v", challenge="c"),
            ),
            patch("cli.auth.commands.generate_state", return_value="s"),
            patch(
                "cli.auth.commands.exchange_code_for_tokens",
                return_value=_fake_token_set("fresh@ubidots.com"),
            ),
        ):
            mock_server.return_value.wait_for_callback.return_value = LoopbackResult(code="code", state="s")
            result = self.runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertNotIn("already has an active OAuth session", result.output)


class _OAuthProfileTestBase(ProfileTestBase):
    def _seed_oauth_profile(self, **overrides):
        base = {
            "api_domain": "https://core.test",
            "auth_method": AuthHeaderTypeEnum.OAUTH2.value,
            "access_token": "access-token-fake",
            "refresh_token": "refresh-token-fake",
            "expires_at": int(time.time()) + 3600,
            "scope": "read write offline_access",
            "token_type": "Bearer",
            "oauth_client_id": "ubidots-cli",
            "runtimes": [],
            "containerRepositoryBase": settings.CONFIG.DEFAULT_CONTAINER_REPOSITORY,
            "output_format": "machine",
        }
        base.update(overrides)
        path = self.profiles_dir / "default.yaml"
        path.write_text(yaml.dump(base))
        return path


class TestLogoutNoOAuthSession(_OAuthProfileTestBase):
    def test_non_oauth_profile_reports_no_session_to_log_out(self):
        with patch("cli.auth.commands.revoke_refresh_token") as mock_revoke:
            result = self.runner.invoke(_logout_app(), [])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("No OAuth session to log out from", result.output)
        mock_revoke.assert_not_called()

    def test_non_oauth_profile_leaves_profile_unchanged(self):
        profile_path = self.profiles_dir / "default.yaml"
        original_contents = profile_path.read_bytes()
        with patch("cli.auth.commands.revoke_refresh_token"):
            self.runner.invoke(_logout_app(), [])
        self.assertEqual(profile_path.read_bytes(), original_contents)


class TestLogoutSuccess(_OAuthProfileTestBase):
    @respx.mock
    def test_successful_logout_clears_credentials_and_confirms(self):
        self._seed_oauth_profile(refresh_token="rt", oauth_client_id="ubidots-cli")
        respx.post("https://core.test/o/revoke_token/").mock(return_value=httpx.Response(200))
        result = self.runner.invoke(_logout_app(), [])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Logged out", result.output)
        saved = yaml.safe_load((self.profiles_dir / "default.yaml").read_text())
        self.assertEqual(saved.get("auth_method"), AuthHeaderTypeEnum.TOKEN.value)
        self.assertEqual(saved.get("refresh_token", ""), "")
        self.assertEqual(saved.get("access_token", ""), "")

    @respx.mock
    def test_successful_logout_does_not_warn_about_token_state(self):
        self._seed_oauth_profile(refresh_token="rt", oauth_client_id="ubidots-cli")
        respx.post("https://core.test/o/revoke_token/").mock(return_value=httpx.Response(200))
        result = self.runner.invoke(_logout_app(), [])
        self.assertNotIn("already invalid", result.output)


class TestLogoutAlreadyInvalid(_OAuthProfileTestBase):
    @respx.mock
    def test_already_revoked_token_clears_credentials_and_notifies(self):
        self._seed_oauth_profile(refresh_token="rt", oauth_client_id="ubidots-cli")
        respx.post("https://core.test/o/revoke_token/").mock(return_value=httpx.Response(401))
        result = self.runner.invoke(_logout_app(), [])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("already invalid", result.output)
        saved = yaml.safe_load((self.profiles_dir / "default.yaml").read_text())
        self.assertEqual(saved.get("auth_method"), AuthHeaderTypeEnum.TOKEN.value)


class TestLogoutNetworkError(_OAuthProfileTestBase):
    @respx.mock
    def test_unreachable_server_still_clears_credentials_locally(self):
        self._seed_oauth_profile(refresh_token="rt", oauth_client_id="ubidots-cli")
        respx.post("https://core.test/o/revoke_token/").mock(side_effect=httpx.ConnectError("unreachable"))
        result = self.runner.invoke(_logout_app(), [])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Could not reach core to revoke remotely", result.output)
        saved = yaml.safe_load((self.profiles_dir / "default.yaml").read_text())
        self.assertEqual(saved.get("refresh_token", ""), "")


class TestLogoutForceRemote(_OAuthProfileTestBase):
    def test_force_remote_flag_attempts_revocation_even_without_oauth_session(self):
        with patch("cli.auth.commands.revoke_refresh_token") as mock_revoke:
            mock_revoke.return_value = RevokeResult(status="already_invalid", http_status=401)
            result = self.runner.invoke(_logout_app(), ["--force-remote"])
        mock_revoke.assert_called_once()
        self.assertEqual(result.exit_code, 0)
        self.assertIn("already invalid", result.output)
        saved = yaml.safe_load((self.profiles_dir / "default.yaml").read_text())
        self.assertEqual(saved.get("auth_method"), AuthHeaderTypeEnum.TOKEN.value)
        self.assertEqual(saved.get("refresh_token", ""), "")
        self.assertEqual(saved.get("access_token", ""), "")


class TestWhoamiTokenProfile(_OAuthProfileTestBase):
    def test_non_oauth_profile_reports_no_session(self):
        with patch("cli.auth.commands.fetch_jwks") as mock_jwks:
            result = self.runner.invoke(_whoami_app(), [])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("No OAuth session", result.output)
        mock_jwks.assert_not_called()


class TestWhoamiPlainOutput(_OAuthProfileTestBase):
    def test_plain_output_contains_expected_fields(self):
        self._seed_oauth_profile(access_token="access.fake.token")
        fake_claims = JwtClaims(
            email="user@test.com",
            user_type="business",
            business_account="acme",
            scope="read write",
            exp=int(time.time()) + 3600,
            raw={},
        )
        with (
            patch("cli.auth.commands.fetch_jwks", return_value=_SAMPLE_JWKS),
            patch("cli.auth.commands.decode_jwt", return_value=fake_claims),
        ):
            result = self.runner.invoke(_whoami_app(), [])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("user@test.com", result.output)
        self.assertIn("business", result.output)
        self.assertIn("acme", result.output)
        self.assertIn("read write", result.output)
        self.assertIn("expires_at", result.output)
        self.assertIn("expires_in", result.output)


class TestWhoamiJsonOutput(_OAuthProfileTestBase):
    def test_json_output_has_correct_keys_and_no_secrets(self):
        self._seed_oauth_profile(access_token="access.fake.token")
        fake_claims = JwtClaims(
            email="user@test.com",
            user_type="business",
            business_account="acme",
            scope="read write",
            exp=int(time.time()) + 3600,
            raw={},
        )
        with (
            patch("cli.auth.commands.fetch_jwks", return_value=_SAMPLE_JWKS),
            patch("cli.auth.commands.decode_jwt", return_value=fake_claims),
        ):
            result = self.runner.invoke(_whoami_app(), ["--json"])
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output.strip())
        self.assertEqual(
            set(data.keys()),
            {"email", "user_type", "business_account", "scopes", "expires_at", "expires_in"},
        )
        self.assertNotIn("access_token", data)
        self.assertNotIn("refresh_token", data)
        self.assertEqual(data["email"], "user@test.com")

    def test_expiry_timestamp_is_in_utc_iso_format(self):
        self._seed_oauth_profile(access_token="access.fake.token")
        fake_claims = JwtClaims(
            email="u@t.com",
            user_type="t",
            business_account="b",
            scope="r",
            exp=int(time.time()) + 300,
            raw={},
        )
        with (
            patch("cli.auth.commands.fetch_jwks", return_value=_SAMPLE_JWKS),
            patch("cli.auth.commands.decode_jwt", return_value=fake_claims),
        ):
            result = self.runner.invoke(_whoami_app(), ["--json"])
        data = json.loads(result.output.strip())
        self.assertTrue(data["expires_at"].endswith("Z"))

    def test_token_at_exact_expiry_is_rejected(self):
        self._seed_oauth_profile(access_token="access.fake.token")
        now_time = int(time.time())
        exp_time = now_time - 1000
        fake_claims = JwtClaims(
            email="u@t.com",
            user_type="t",
            business_account="b",
            scope="r",
            exp=exp_time,
            raw={},
        )
        with (
            patch("cli.auth.commands.fetch_jwks", return_value=_SAMPLE_JWKS),
            patch("cli.auth.commands.decode_jwt", return_value=fake_claims),
            patch("cli.auth.commands.datetime") as mock_dt,
        ):
            mock_now = MagicMock()
            mock_now.timestamp.return_value = exp_time
            mock_dt.now.return_value = mock_now
            mock_dt.timezone = timezone
            mock_dt.fromtimestamp = datetime.fromtimestamp
            result = self.runner.invoke(_whoami_app(), ["--json"])
        self.assertEqual(result.exit_code, 3)


class TestWhoamiExpiredToken(_OAuthProfileTestBase):
    def test_expired_token_fails_with_session_expired_message(self):
        self._seed_oauth_profile(access_token="access.fake.token")
        fake_claims = JwtClaims(
            email="u@t.com",
            user_type="t",
            business_account="b",
            scope="r",
            exp=int(time.time()) - 10,
            raw={},
        )
        with (
            patch("cli.auth.commands.fetch_jwks", return_value=_SAMPLE_JWKS),
            patch("cli.auth.commands.decode_jwt", return_value=fake_claims),
        ):
            result = self.runner.invoke(_whoami_app(), [])
        self.assertEqual(result.exit_code, 3)
        self.assertIn("Session expired", result.output)


class TestWhoamiInvalidSignature(_OAuthProfileTestBase):
    def test_tampered_token_fails_with_invalid_token_message(self):
        self._seed_oauth_profile(access_token="access.fake.token")
        with (
            patch("cli.auth.commands.fetch_jwks", return_value=_SAMPLE_JWKS),
            patch("cli.auth.commands.decode_jwt", side_effect=InvalidTokenSignatureError("bad sig")),
        ):
            result = self.runner.invoke(_whoami_app(), [])
        self.assertEqual(result.exit_code, 5)
        self.assertIn("Invalid token", result.output)


class TestWhoamiJwksUnavailable(_OAuthProfileTestBase):
    def test_jwks_unavailable_fails_with_error(self):
        self._seed_oauth_profile(access_token="access.fake.token")
        with patch("cli.auth.commands.fetch_jwks", side_effect=JwksUnavailableError()):
            result = self.runner.invoke(_whoami_app(), [])
        self.assertNotEqual(result.exit_code, 0)
