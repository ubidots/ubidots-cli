import base64
import json
import os
import time
from unittest.mock import patch

import pytest
import typer
import yaml
from typer.testing import CliRunner

from cli.auth.commands import whoami
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
    return profiles_dir


def _whoami_app():
    app = typer.Typer()
    app.command()(whoami)
    return app


def _mock_jwt(claims: dict) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps(claims).encode()
    ).rstrip(b"=").decode()
    return f"{header}.{payload}.sig"


def _seed_oauth_profile(profiles_dir, claims, expires_at=None, name="default"):
    expires_at = expires_at if expires_at is not None else int(time.time()) + 900
    data = {
        "api_domain": "https://core.test",
        "auth_method": AuthHeaderTypeEnum.OAUTH2.value,
        "access_token": _mock_jwt({**claims, "exp": expires_at}),
        "refresh_token": "r-token",
        "expires_at": expires_at,
        "oauth_client_id": "ubidots-cli",
        "scope": claims.get("scope", "read write"),
        "token_type": "Bearer",
        "runtimes": [],
        "containerRepositoryBase": settings.CONFIG.DEFAULT_CONTAINER_REPOSITORY,
        "output_format": "machine",
    }
    profile_path = profiles_dir / f"{name}.yaml"
    profile_path.write_text(yaml.dump(data))
    if os.name != "nt":
        os.chmod(profile_path, 0o600)
    return profile_path


def _seed_token_profile(profiles_dir, name="default"):
    data = {
        "api_domain": "https://core.test",
        "auth_method": AuthHeaderTypeEnum.TOKEN.value,
        "access_token": "static",
        "runtimes": [],
        "containerRepositoryBase": settings.CONFIG.DEFAULT_CONTAINER_REPOSITORY,
        "output_format": "machine",
    }
    profile_path = profiles_dir / f"{name}.yaml"
    profile_path.write_text(yaml.dump(data))
    if os.name != "nt":
        os.chmod(profile_path, 0o600)


class TestWhoamiHumanOutput:
    def test_oauth_profile_prints_full_summary_with_every_expected_line(
        self, cli_runner, isolated_profile_dir, monkeypatch
    ):
        # Setup — freeze time so expires_in is deterministic
        now = 1_700_000_000
        monkeypatch.setattr(time, "time", lambda: now)
        expires_at = now + 600
        _seed_oauth_profile(
            isolated_profile_dir,
            claims={
                "email": "gustavo@ubidots.com",
                "user_type": "admin",
                "business_account": "ubidots",
                "scope": "read write",
            },
            expires_at=expires_at,
        )
        expected_lines = [
            "profile         : default",
            "email           : gustavo@ubidots.com",
            "user_type       : admin",
            "business_account: ubidots",
            "scopes          : read write",
            f"expires_at      : {expires_at}",
            "expires_in      : 600s",
            "signature       : unverified (JWKS unavailable)",
        ]
        # Action
        with patch("cli.auth.commands.fetch_jwks", return_value=None):
            result = cli_runner.invoke(_whoami_app(), [])
        actual_lines = result.output.strip().splitlines()
        # Expected
        assert result.exit_code == 0
        assert actual_lines == expected_lines


class TestWhoamiJSONOutput:
    def test_json_output_is_full_payload_and_does_not_leak_tokens(
        self, cli_runner, isolated_profile_dir, monkeypatch
    ):
        # Setup — freeze time so expires_in is deterministic
        now = 1_700_000_000
        monkeypatch.setattr(time, "time", lambda: now)
        expires_at = now + 600
        _seed_oauth_profile(
            isolated_profile_dir,
            claims={
                "email": "dev@ubidots.com",
                "user_type": "regular",
                "business_account": "acme",
                "scope": "read",
            },
            expires_at=expires_at,
        )
        expected_payload = {
            "profile": "default",
            "email": "dev@ubidots.com",
            "user_type": "regular",
            "business_account": "acme",
            "scopes": "read",
            "expires_at": expires_at,
            "expires_in": 600,
            "signature": "unverified (JWKS unavailable)",
        }
        # Action
        with patch("cli.auth.commands.fetch_jwks", return_value=None):
            result = cli_runner.invoke(_whoami_app(), ["--json"])
        actual_payload = json.loads(result.output.strip())
        # Expected — full payload, no leaked tokens
        assert result.exit_code == 0
        assert actual_payload == expected_payload
        assert "access_token" not in result.output
        assert "refresh_token" not in result.output


class TestWhoamiTokenProfile:
    def test_token_only_profile_says_no_oauth_session_and_exits_zero(
        self, cli_runner, isolated_profile_dir
    ):
        # Setup
        _seed_token_profile(isolated_profile_dir)
        # Action
        result = cli_runner.invoke(_whoami_app(), [])
        # Expected
        assert result.exit_code == 0
        assert "No OAuth session" in result.output

    def test_token_profile_json_returns_full_error_payload(
        self, cli_runner, isolated_profile_dir
    ):
        # Setup
        _seed_token_profile(isolated_profile_dir)
        expected_payload = {
            "error": "No OAuth session. Profile is using a static API token.",
            "profile": "default",
        }
        # Action
        result = cli_runner.invoke(_whoami_app(), ["--json"])
        actual_payload = json.loads(result.output.strip())
        # Expected
        assert result.exit_code == 0
        assert actual_payload == expected_payload


class TestWhoamiSessionExpired:
    def test_expired_session_exits_with_error_and_does_not_refresh(
        self, cli_runner, isolated_profile_dir
    ):
        # Setup — exp 1h in the past
        _seed_oauth_profile(
            isolated_profile_dir,
            claims={"email": "old@ubidots.com"},
            expires_at=int(time.time()) - 3600,
        )
        # Action
        with patch("cli.auth.commands.fetch_jwks", return_value=None):
            result = cli_runner.invoke(_whoami_app(), [])
        # Expected
        assert result.exit_code != 0
        assert "Session expired" in result.output
        assert "ubidots login" in result.output


class TestWhoamiSkipSignature:
    def test_skip_signature_avoids_jwks_call(self, cli_runner, isolated_profile_dir):
        # Setup
        _seed_oauth_profile(
            isolated_profile_dir,
            claims={"email": "dev@ubidots.com"},
            expires_at=int(time.time()) + 600,
        )
        # Action
        with patch("cli.auth.commands.fetch_jwks") as mock_fetch:
            result = cli_runner.invoke(_whoami_app(), ["--skip-signature"])
        # Expected
        assert result.exit_code == 0
        assert "skipped" in result.output
        mock_fetch.assert_not_called()
