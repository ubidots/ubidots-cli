import base64
import json
import os
import stat
from unittest.mock import patch

import httpx
import pytest
import respx
import typer
import yaml
from typer.testing import CliRunner

from cli.auth.commands import CLIENT_ID_ENV_VAR
from cli.auth.commands import login
from cli.auth.loopback_server import LoopbackResult
from cli.auth.oauth_client import PKCEPair
from cli.auth.oauth_client import TokenSet
from cli.commons.enums import OutputFormatFieldsEnum
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
    (tmp_path / "config.yaml").write_text(
        yaml.dump({"profilesPath": str(profiles_dir), "profile": "default"})
    )
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
        os.chmod(legacy_path, 0o600)
    return profiles_dir


def _jwt_with_email(email: str) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps({"email": email}).encode()
    ).rstrip(b"=").decode()
    return f"{header}.{payload}.sig"


def _login_app():
    app = typer.Typer()
    app.command()(login)
    return app


def _fake_token_set(email: str = "u@ubidots.com") -> TokenSet:
    return TokenSet(
        access_token=_jwt_with_email(email),
        refresh_token="r-token",
        token_type="Bearer",
        expires_at=10_000_000_000,
        scope="read write",
    )


class TestLoginHappyPath:
    @respx.mock
    def test_login_persists_full_oauth_profile_yaml(
        self, cli_runner, isolated_profile_dir
    ):
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
            mock_server.return_value.wait_for_callback.return_value = LoopbackResult(
                code="THECODE", state="s"
            )
            result = cli_runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        actual_yaml = yaml.safe_load((isolated_profile_dir / "default.yaml").read_text())
        actual_expires_at = actual_yaml.pop("expires_at")
        # Expected
        assert result.exit_code == 0, result.output
        assert "Login successful as dev@ubidots.com" in result.output
        assert actual_yaml == expected_yaml_keys
        assert actual_expires_at > 0


class TestLoginErrorPaths:
    def test_state_mismatch_aborts_and_leaves_legacy_profile_intact(
        self, cli_runner, isolated_profile_dir
    ):
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
            mock_server.return_value.wait_for_callback.return_value = LoopbackResult(
                code="code", state="evil"
            )
            result = cli_runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        actual_yaml = yaml.safe_load((isolated_profile_dir / "default.yaml").read_text())
        # Expected
        assert result.exit_code != 0
        assert "CSRF mismatch" in result.output
        assert actual_yaml == expected_yaml_after

    def test_no_browser_prints_authorize_url_without_opening_browser(
        self, cli_runner, isolated_profile_dir
    ):
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
            mock_server.return_value.wait_for_callback.return_value = LoopbackResult(
                code="code", state="s"
            )
            result = cli_runner.invoke(
                _login_app(), ["--client-id", "ubidots-cli", "--no-browser"]
            )
        # Expected
        assert result.exit_code == 0
        opener.assert_not_called()
        assert "/o/authorize/" in result.output

    def test_port_already_in_use_exits_with_code_2(self, cli_runner, isolated_profile_dir):
        # Setup
        expected_exit_code = 2
        # Action
        with patch("cli.auth.commands.port_available", return_value=False):
            result = cli_runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        # Expected
        assert result.exit_code == expected_exit_code
        assert "already in use" in result.output


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
            mock_server.return_value.wait_for_callback.return_value = LoopbackResult(
                code="code", state="s"
            )
            cli_runner.invoke(_login_app(), ["--client-id", "ubidots-cli"])
        actual_mode = stat.S_IMODE((isolated_profile_dir / "default.yaml").stat().st_mode)
        # Expected
        assert actual_mode == expected_mode


class TestClientIdResolution:
    def test_no_client_id_anywhere_exits_with_hint(
        self, cli_runner, isolated_profile_dir, monkeypatch
    ):
        # Setup
        monkeypatch.delenv(CLIENT_ID_ENV_VAR, raising=False)
        monkeypatch.setattr(settings.OAUTH, "DEFAULT_CLIENT_ID", "")
        expected_exit_code = 2
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
            mock_server.return_value.wait_for_callback.return_value = LoopbackResult(
                code="code", state="s"
            )
            result = cli_runner.invoke(_login_app(), [])
        saved_yaml = yaml.safe_load((isolated_profile_dir / "default.yaml").read_text())
        # Expected
        assert result.exit_code == 0
        assert mock_exchange.call_args.kwargs["client_id"] == expected_client_id
        assert saved_yaml["oauth_client_id"] == expected_client_id

    def test_flag_overrides_env_and_settings(
        self, cli_runner, isolated_profile_dir, monkeypatch
    ):
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
            mock_server.return_value.wait_for_callback.return_value = LoopbackResult(
                code="code", state="s"
            )
            result = cli_runner.invoke(_login_app(), ["--client-id", "from-flag"])
        # Expected
        assert result.exit_code == 0
        assert mock_exchange.call_args.kwargs["client_id"] == expected_client_id

    def test_settings_default_is_used_when_no_flag_and_no_env(
        self, cli_runner, isolated_profile_dir, monkeypatch
    ):
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
            mock_server.return_value.wait_for_callback.return_value = LoopbackResult(
                code="code", state="s"
            )
            result = cli_runner.invoke(_login_app(), [])
        # Expected
        assert result.exit_code == 0
        assert mock_exchange.call_args.kwargs["client_id"] == expected_client_id
