import base64
import json
import os
import pathlib
import stat
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
from cli.auth.loopback_server import LoopbackResult
from cli.auth.oauth_client import PKCEPair
from cli.auth.oauth_client import TokenSet
from cli.commons.enums import OutputFormatFieldsEnum
from cli.commons.exceptions import AuthorizationDeniedError
from cli.commons.exceptions import LoginTimeoutError
from cli.commons.exceptions import TokenExchangeError
from cli.commons.exceptions import UnknownOAuthClientError
from cli.config.models import AuthHeaderTypeEnum
from cli.settings import settings


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def isolated_profile_dir(tmp_path, monkeypatch):
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    monkeypatch.setattr(settings.CONFIG, "DIRECTORY_PATH", tmp_path)
    monkeypatch.setattr(settings.CONFIG, "PROFILES_PATH", profiles_dir)
    monkeypatch.setattr(settings.CONFIG, "FILE_PATH", tmp_path / "config.yaml")
    (tmp_path / "config.yaml").write_text(yaml.dump({"profilesPath": str(profiles_dir), "profile": "default"}))
    legacy_profile = {
        "api_domain": "https://core.test",
        "auth_method": AuthHeaderTypeEnum.TOKEN.value,
        "access_token": "legacy",
        "runtimes": [],
        "containerRepositoryBase": settings.CONFIG.DEFAULT_CONTAINER_REPOSITORY,
        "output_format": "machine",
    }
    legacy_path = profiles_dir / "default.yaml"
    legacy_path.write_text(yaml.dump(legacy_profile))
    if os.name != "nt":
        pathlib.Path(legacy_path).chmod(0o600)
    return profiles_dir


def _jwt_with_email(email: str) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(json.dumps({"email": email}).encode()).rstrip(b"=").decode()
    return f"{header}.{payload}.sig"


def _login_app():
    app = typer.Typer()
    app.command()(login)
    return app


def _fake_token_set(email: str = "u@ubidots.com") -> TokenSet:
    return TokenSet(
        access_token=_jwt_with_email(email),
        refresh_token="refresh-token-fake-abcdef",
        token_type="Bearer",
        expires_at=10_000_000_000,
        scope="read write",
    )


class TestLoginHappyPath:
    @respx.mock
    def test_login_persists_full_oauth_profile_yaml(self, cli_runner, isolated_profile_dir):
        # Setup
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
        # Action
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
            result = cli_runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        actual_yaml = yaml.safe_load((isolated_profile_dir / "default.yaml").read_text())
        actual_expires_at = actual_yaml.pop("expires_at")
        # Expected
        assert result.exit_code == 0, result.output
        assert "Login successful as dev@ubidots.com" in result.output
        assert actual_yaml == expected_yaml_keys
        assert actual_expires_at > 0


class TestLoginErrorPaths:
    def test_state_mismatch_aborts_and_leaves_legacy_profile_intact(self, cli_runner, isolated_profile_dir):
        # Setup
        expected_yaml_after = {
            "api_domain": "https://core.test",
            "auth_method": AuthHeaderTypeEnum.TOKEN.value,
            "access_token": "legacy",
            "runtimes": [],
            "containerRepositoryBase": settings.CONFIG.DEFAULT_CONTAINER_REPOSITORY,
            "output_format": OutputFormatFieldsEnum.MACHINE.value,
        }
        # Action
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
            result = cli_runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        actual_yaml = yaml.safe_load((isolated_profile_dir / "default.yaml").read_text())
        # Expected
        assert result.exit_code == 4
        assert "CSRF mismatch" in result.output
        assert actual_yaml == expected_yaml_after

    def test_no_browser_prints_authorize_url_without_opening_browser(self, cli_runner, isolated_profile_dir):
        # Setup
        # Action
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
            result = cli_runner.invoke(_login_app(), ["--client-id", "ubidots-cli", "--no-browser"])
        # Expected
        assert result.exit_code == 0
        opener.assert_not_called()
        assert "/o/authorize/" in result.output


class TestLoginFilePermissions:
    @pytest.mark.skipif(os.name == "nt", reason="POSIX-only")
    def test_login_writes_profile_with_mode_0600(self, cli_runner, isolated_profile_dir):
        # Setup
        expected_mode = 0o600
        # Action
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
            cli_runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        actual_mode = stat.S_IMODE((isolated_profile_dir / "default.yaml").stat().st_mode)
        # Expected
        assert actual_mode == expected_mode


class TestClientIdResolution:
    def test_no_client_id_anywhere_exits_with_hint(self, cli_runner, isolated_profile_dir, monkeypatch):
        # Setup
        monkeypatch.delenv(CLIENT_ID_ENV_VAR, raising=False)
        monkeypatch.setattr(settings.OAUTH, "DEFAULT_CLIENT_ID", "")
        expected_exit_code = 64
        # Action
        with patch("cli.auth.commands.port_available", return_value=True):
            result = cli_runner.invoke(_login_app(), [])
        # Expected
        assert result.exit_code == expected_exit_code
        assert CLIENT_ID_ENV_VAR in result.output

    def test_env_var_supplies_client_id_when_flag_and_settings_absent(
        self, cli_runner, isolated_profile_dir, monkeypatch
    ):
        # Setup
        monkeypatch.setenv(CLIENT_ID_ENV_VAR, "from-env")
        monkeypatch.setattr(settings.OAUTH, "DEFAULT_CLIENT_ID", "")
        expected_client_id = "from-env"
        # Action
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
            result = cli_runner.invoke(_login_app(), [])
        saved_yaml = yaml.safe_load((isolated_profile_dir / "default.yaml").read_text())
        # Expected
        assert result.exit_code == 0
        assert mock_exchange.call_args.kwargs["client_id"] == expected_client_id
        assert saved_yaml["oauth_client_id"] == expected_client_id

    def test_flag_overrides_env_and_settings(self, cli_runner, isolated_profile_dir, monkeypatch):
        # Setup
        monkeypatch.setenv(CLIENT_ID_ENV_VAR, "from-env")
        monkeypatch.setattr(settings.OAUTH, "DEFAULT_CLIENT_ID", "from-settings")
        expected_client_id = "from-flag"
        # Action
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
            result = cli_runner.invoke(_login_app(), ["--client-id", "from-flag"])
        # Expected
        assert result.exit_code == 0
        assert mock_exchange.call_args.kwargs["client_id"] == expected_client_id

    def test_settings_default_is_used_when_no_flag_and_no_env(self, cli_runner, isolated_profile_dir, monkeypatch):
        # Setup
        monkeypatch.delenv(CLIENT_ID_ENV_VAR, raising=False)
        monkeypatch.setattr(settings.OAUTH, "DEFAULT_CLIENT_ID", "ubidots-cli")
        expected_client_id = "ubidots-cli"
        # Action
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
            result = cli_runner.invoke(_login_app(), [])
        # Expected
        assert result.exit_code == 0
        assert mock_exchange.call_args.kwargs["client_id"] == expected_client_id

    def test_profile_oauth_client_id_used_when_no_flag_no_env(self, cli_runner, tmp_path, monkeypatch):
        # Setup — profile already has oauth_client_id; no flag or env override
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        monkeypatch.setattr(settings.CONFIG, "DIRECTORY_PATH", tmp_path)
        monkeypatch.setattr(settings.CONFIG, "PROFILES_PATH", profiles_dir)
        monkeypatch.setattr(settings.CONFIG, "FILE_PATH", tmp_path / "config.yaml")
        monkeypatch.setattr(settings.OAUTH, "DEFAULT_CLIENT_ID", "")
        monkeypatch.delenv(CLIENT_ID_ENV_VAR, raising=False)
        (tmp_path / "config.yaml").write_text(yaml.dump({"profilesPath": str(profiles_dir), "profile": "default"}))
        profile_with_client = {
            "api_domain": "https://core.test",
            "auth_method": AuthHeaderTypeEnum.TOKEN.value,
            "access_token": "tok",
            "oauth_client_id": "from-profile",
            "runtimes": [],
            "containerRepositoryBase": settings.CONFIG.DEFAULT_CONTAINER_REPOSITORY,
            "output_format": "machine",
        }
        profile_file = profiles_dir / "default.yaml"
        profile_file.write_text(yaml.dump(profile_with_client))
        pathlib.Path(profile_file).chmod(0o600)
        expected_client_id = "from-profile"
        # Action
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
            result = cli_runner.invoke(_login_app(), [])
        # Expected
        assert result.exit_code == 0
        assert mock_exchange.call_args.kwargs["client_id"] == expected_client_id


class TestPortResolution:
    def test_default_port_is_53682_when_no_flag_no_env(self, cli_runner, isolated_profile_dir, monkeypatch):
        # Setup
        monkeypatch.delenv(LOOPBACK_PORT_ENV_VAR, raising=False)
        expected_redirect_uri = "http://127.0.0.1:53682/callback"
        # Action
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
            result = cli_runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        # Expected
        assert result.exit_code == 0
        assert mock_port_check.call_args.kwargs == {"port": 53682}
        mock_server.assert_called_once_with(port=53682)
        assert mock_exchange.call_args.kwargs["redirect_uri"] == expected_redirect_uri

    def test_flag_overrides_default_port_in_redirect_uri_and_server(
        self, cli_runner, isolated_profile_dir, monkeypatch
    ):
        # Setup
        monkeypatch.delenv(LOOPBACK_PORT_ENV_VAR, raising=False)
        expected_port = 65000
        expected_redirect_uri = "http://127.0.0.1:65000/callback"
        # Action
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
            result = cli_runner.invoke(_login_app(), ["--client-id", "ubidots-cli", "--port", "65000"])
        # Expected
        assert result.exit_code == 0
        assert mock_port_check.call_args.kwargs == {"port": expected_port}
        mock_server.assert_called_once_with(port=expected_port)
        assert mock_exchange.call_args.kwargs["redirect_uri"] == expected_redirect_uri

    def test_env_var_supplies_port_when_flag_absent(self, cli_runner, isolated_profile_dir, monkeypatch):
        # Setup
        monkeypatch.setenv(LOOPBACK_PORT_ENV_VAR, "60000")
        expected_port = 60000
        # Action
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
            result = cli_runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        # Expected
        assert result.exit_code == 0
        assert mock_port_check.call_args.kwargs == {"port": expected_port}
        mock_server.assert_called_once_with(port=expected_port)

    def test_port_in_use_message_lists_diagnostic_commands(self, cli_runner, isolated_profile_dir, monkeypatch):
        # Setup
        monkeypatch.delenv(LOOPBACK_PORT_ENV_VAR, raising=False)
        expected_exit_code = 64
        # Action
        with patch("cli.auth.commands.port_available", return_value=False):
            result = cli_runner.invoke(_login_app(), ["--client-id", "ubidots-cli", "--port", "53682"])
        # Expected
        assert result.exit_code == expected_exit_code
        assert "lsof" in result.output
        assert "--port" in result.output
        assert LOOPBACK_PORT_ENV_VAR in result.output


class TestApiDomainResolution:
    def test_flag_overrides_profile_api_domain_and_is_persisted(self, cli_runner, isolated_profile_dir, monkeypatch):
        # Setup
        monkeypatch.delenv(API_DOMAIN_ENV_VAR, raising=False)
        expected_api_domain = "https://cs.ubidots.site"
        # Action
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
            result = cli_runner.invoke(
                _login_app(),
                [
                    "--client-id",
                    "ubidots-cli",
                    "--api-domain",
                    expected_api_domain,
                ],
            )
        saved_yaml = yaml.safe_load((isolated_profile_dir / "default.yaml").read_text())
        # Expected
        assert result.exit_code == 0
        assert mock_exchange.call_args.kwargs["api_domain"] == expected_api_domain
        assert saved_yaml["api_domain"] == expected_api_domain

    def test_env_var_supplies_api_domain_when_flag_absent(self, cli_runner, isolated_profile_dir, monkeypatch):
        # Setup
        monkeypatch.setenv(API_DOMAIN_ENV_VAR, "https://cs.ubidots.site")
        expected_api_domain = "https://cs.ubidots.site"
        # Action
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
            result = cli_runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        # Expected
        assert result.exit_code == 0
        assert mock_exchange.call_args.kwargs["api_domain"] == expected_api_domain

    def test_profile_api_domain_used_when_no_flag_no_env(self, cli_runner, isolated_profile_dir, monkeypatch):
        # Setup — fixture creates legacy profile with api_domain=https://core.test
        monkeypatch.delenv(API_DOMAIN_ENV_VAR, raising=False)
        expected_api_domain = "https://core.test"
        # Action
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
            result = cli_runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        # Expected
        assert result.exit_code == 0
        assert mock_exchange.call_args.kwargs["api_domain"] == expected_api_domain


class TestProfileResolution:
    def test_no_profile_flag_writes_to_active_profile_not_default(self, cli_runner, tmp_path, monkeypatch):
        # Setup: active profile is "staging", NOT "default"
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        monkeypatch.setattr(settings.CONFIG, "DIRECTORY_PATH", tmp_path)
        monkeypatch.setattr(settings.CONFIG, "PROFILES_PATH", profiles_dir)
        monkeypatch.setattr(settings.CONFIG, "FILE_PATH", tmp_path / "config.yaml")
        (tmp_path / "config.yaml").write_text(yaml.dump({"profilesPath": str(profiles_dir), "profile": "staging"}))
        staging_profile = {
            "api_domain": "https://staging.test",
            "auth_method": AuthHeaderTypeEnum.TOKEN.value,
            "access_token": "legacy-staging",
            "runtimes": [],
            "containerRepositoryBase": settings.CONFIG.DEFAULT_CONTAINER_REPOSITORY,
            "output_format": "machine",
        }
        staging_path = profiles_dir / "staging.yaml"
        staging_path.write_text(yaml.dump(staging_profile))
        if os.name != "nt":
            pathlib.Path(staging_path).chmod(0o600)
        # Action
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
            result = cli_runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        # Expected — tokens persist in staging.yaml, default.yaml never created
        assert result.exit_code == 0, result.output
        assert "profile 'staging'" in result.output
        saved = yaml.safe_load(staging_path.read_text())
        assert saved["auth_method"] == AuthHeaderTypeEnum.OAUTH2.value
        assert saved["refresh_token"]
        assert not (profiles_dir / "default.yaml").exists()

    def test_explicit_profile_flag_creates_new_profile_if_missing(self, cli_runner, isolated_profile_dir):
        # Setup — fixture creates only default.yaml; "fresh" does not exist
        new_profile_path = isolated_profile_dir / "fresh.yaml"
        assert not new_profile_path.exists()
        # Action
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
            result = cli_runner.invoke(
                _login_app(),
                ["--client-id", "ubidots-cli", "--profile", "fresh"],
            )
        # Expected
        assert result.exit_code == 0, result.output
        assert "does not exist yet" in result.output
        assert new_profile_path.exists()
        saved = yaml.safe_load(new_profile_path.read_text())
        assert saved["auth_method"] == AuthHeaderTypeEnum.OAUTH2.value

    def test_explicit_profile_flag_only_touches_target_profile(self, cli_runner, isolated_profile_dir):
        # Setup — fixture creates default.yaml; we'll login to "other"
        default_before = (isolated_profile_dir / "default.yaml").read_text()
        # Action
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
            result = cli_runner.invoke(
                _login_app(),
                ["--client-id", "ubidots-cli", "--profile", "other"],
            )
        default_after = (isolated_profile_dir / "default.yaml").read_text()
        # Expected — default profile is untouched
        assert result.exit_code == 0, result.output
        assert default_before == default_after


class TestActiveSessionConfirmation:
    def _seed_oauth_profile(self, profiles_dir, profile_name="default"):
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
        profile_path = profiles_dir / f"{profile_name}.yaml"
        profile_path.write_text(yaml.dump(profile_data))
        if os.name != "nt":
            pathlib.Path(profile_path).chmod(0o600)

    def test_active_oauth_session_prompts_for_confirmation_and_aborts_on_no(self, cli_runner, isolated_profile_dir):
        # Setup — replace default.yaml with an already-authenticated OAuth profile
        self._seed_oauth_profile(isolated_profile_dir)
        # Action — user types "n" to the prompt
        with (
            patch("cli.auth.commands.port_available", return_value=True),
            patch("cli.auth.commands.LoopbackServer"),
        ):
            result = cli_runner.invoke(_login_app(), ["--client-id", "ubidots-cli"], input="n\n")
        # Expected
        assert result.exit_code != 0
        assert "already has an active OAuth session" in result.output
        assert "existing@ubidots.com" in result.output
        assert "Aborted by user" in result.output

    def test_yes_flag_skips_confirmation_prompt(self, cli_runner, isolated_profile_dir):
        # Setup
        self._seed_oauth_profile(isolated_profile_dir)
        # Action
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
            result = cli_runner.invoke(_login_app(), ["--client-id", "ubidots-cli", "--yes"])
        # Expected
        assert result.exit_code == 0, result.output
        assert "new@ubidots.com" in result.output


class TestErrorPaths:
    def test_authorization_denied_exits_with_code_2(self, cli_runner, isolated_profile_dir):
        # Setup / Action
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
            result = cli_runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        # Expected
        assert result.exit_code == 2
        assert "Authorization denied" in result.output

    def test_login_timeout_exits_with_code_3(self, cli_runner, isolated_profile_dir):
        # Setup / Action
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
            result = cli_runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        # Expected
        assert result.exit_code == 3
        assert "timed out" in result.output.lower()

    def test_unknown_oauth_client_exits_with_code_5(self, cli_runner, isolated_profile_dir):
        # Setup / Action
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
            result = cli_runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        # Expected
        assert result.exit_code == 5
        assert "Unknown OAuth client" in result.output

    def test_token_exchange_failure_exits_with_code_5(self, cli_runner, isolated_profile_dir):
        # Setup / Action
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
            result = cli_runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        # Expected
        assert result.exit_code == 5


class TestRedactionAndVerbose:
    def test_verbose_prints_redirect_uri_and_authorize_url(self, cli_runner, isolated_profile_dir):
        # Setup / Action
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
            result = cli_runner.invoke(
                _login_app(),
                ["--client-id", "ubidots-cli", "--no-browser", "--verbose"],
            )
        # Expected
        assert result.exit_code == 0, result.output
        assert "redirect_uri:" in result.output
        assert "/o/authorize/" in result.output

    def test_verifier_never_appears_in_output(self, cli_runner, isolated_profile_dir):
        # Setup
        long_verifier = "V" * 64
        # Action
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
            result = cli_runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        # Expected
        assert result.exit_code == 0, result.output
        assert long_verifier not in result.output

    def test_authorization_code_never_appears_in_output(self, cli_runner, isolated_profile_dir):
        # Setup
        distinctive_code = "AUTHCODEABCDEF123456"
        # Action
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
            result = cli_runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        # Expected
        assert result.exit_code == 0, result.output
        assert distinctive_code not in result.output

    def test_access_and_refresh_tokens_not_in_output(self, cli_runner, isolated_profile_dir):
        # Setup
        token_set = _fake_token_set("clean@ubidots.com")
        # Action
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
            result = cli_runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        # Expected
        assert result.exit_code == 0, result.output
        assert token_set.access_token not in result.output
        assert token_set.refresh_token not in result.output

    def test_default_scope_in_authorize_url(self, cli_runner, isolated_profile_dir):
        # Setup / Action — --no-browser prints the authorize URL
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
            result = cli_runner.invoke(_login_app(), ["--client-id", "ubidots-cli", "--no-browser"])
        # Expected — URL-encoded scope contains "read", "write", and "offline_access"
        assert result.exit_code == 0, result.output
        assert "read" in result.output
        assert "write" in result.output
        assert "offline_access" in result.output

    def test_custom_scope_flag_in_authorize_url(self, cli_runner, isolated_profile_dir):
        # Setup / Action
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
            result = cli_runner.invoke(
                _login_app(),
                ["--client-id", "ubidots-cli", "--no-browser", "--scope", "read:data"],
            )
        # Expected — custom scope appears in the printed authorize URL
        assert result.exit_code == 0, result.output
        assert "read%3Adata" in result.output or "read:data" in result.output


class TestBrowserAndServerEdgeCases:
    def test_browser_open_fails_prints_fallback_url(self, cli_runner, isolated_profile_dir):
        # Setup / Action — webbrowser.open returns False (no browser available)
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
            result = cli_runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        # Expected — fallback URL is printed when browser can't open
        assert result.exit_code == 0, result.output
        assert "/o/authorize/" in result.output

    def test_loopback_server_oserror_exits_with_code_64(self, cli_runner, isolated_profile_dir):
        # Setup / Action — LoopbackServer raises OSError on bind (port race)
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
            result = cli_runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        # Expected
        assert result.exit_code == 64

    def test_custom_timeout_passed_to_wait_for_callback(self, cli_runner, isolated_profile_dir):
        # Setup / Action
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
            result = cli_runner.invoke(_login_app(), ["--client-id", "ubidots-cli", "--timeout", "42"])
        # Expected
        assert result.exit_code == 0, result.output
        assert mock_server.return_value.wait_for_callback.call_args.kwargs["timeout"] == 42


class TestActiveSessionExpiry:
    def test_expired_oauth_session_does_not_prompt_for_confirmation(self, cli_runner, isolated_profile_dir):
        # Setup — profile has OAuth tokens but expires_at is in the past
        expired_profile = {
            "api_domain": "https://core.test",
            "auth_method": AuthHeaderTypeEnum.OAUTH2.value,
            "access_token": _jwt_with_email("old@ubidots.com"),
            "refresh_token": "old-refresh",
            "expires_at": 1,  # Unix epoch + 1s — always expired
            "oauth_client_id": "ubidots-cli",
            "scope": "read write",
            "token_type": "Bearer",
            "runtimes": [],
            "containerRepositoryBase": settings.CONFIG.DEFAULT_CONTAINER_REPOSITORY,
            "output_format": "machine",
        }
        (isolated_profile_dir / "default.yaml").write_text(yaml.dump(expired_profile))
        # Action — no input provided; if prompt appeared it would block/fail
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
            result = cli_runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        # Expected — login succeeds without any confirmation prompt
        assert result.exit_code == 0, result.output
        assert "already has an active OAuth session" not in result.output
