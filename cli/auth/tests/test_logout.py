import os

import httpx
import pytest
import respx
import typer
import yaml
from typer.testing import CliRunner

from cli.auth.commands import logout
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


def _logout_app():
    app = typer.Typer()
    app.command()(logout)
    return app


def _seed_oauth_profile(profiles_dir, name="default", refresh_token="r-token"):
    data = {
        "api_domain": "https://core.test",
        "auth_method": AuthHeaderTypeEnum.OAUTH2.value,
        "access_token": "jwt-access",
        "refresh_token": refresh_token,
        "expires_at": 10_000_000_000,
        "oauth_client_id": "ubidots-cli",
        "scope": "read write",
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
    return profile_path


class TestLogoutHappyPath:
    @respx.mock
    def test_revoke_200_clears_oauth_fields_and_keeps_token_auth_method(
        self, cli_runner, isolated_profile_dir
    ):
        # Setup
        profile_path = _seed_oauth_profile(isolated_profile_dir)
        route = respx.post("https://core.test/o/revoke_token/").mock(
            return_value=httpx.Response(200)
        )
        # Action
        result = cli_runner.invoke(_logout_app(), [])
        saved = yaml.safe_load(profile_path.read_text())
        sent_body = route.calls[0].request.content.decode("utf-8")
        # Expected
        assert result.exit_code == 0
        assert "Logged out" in result.output
        assert saved["auth_method"] == AuthHeaderTypeEnum.TOKEN.value
        assert saved["access_token"] == ""
        assert "refresh_token" not in saved or not saved["refresh_token"]
        assert "oauth_client_id" not in saved or not saved["oauth_client_id"]
        assert "token=r-token" in sent_body
        assert "client_id=ubidots-cli" in sent_body


class TestLogoutErrorPaths:
    @respx.mock
    def test_revoke_4xx_still_clears_local_credentials(
        self, cli_runner, isolated_profile_dir
    ):
        # Setup
        profile_path = _seed_oauth_profile(isolated_profile_dir)
        respx.post("https://core.test/o/revoke_token/").mock(
            return_value=httpx.Response(401, json={"error": "invalid_token"})
        )
        # Action
        result = cli_runner.invoke(_logout_app(), [])
        saved = yaml.safe_load(profile_path.read_text())
        # Expected
        assert result.exit_code == 0
        assert "already invalid" in result.output
        assert saved["auth_method"] == AuthHeaderTypeEnum.TOKEN.value

    @respx.mock
    def test_network_error_clears_local_and_hints_force_remote(
        self, cli_runner, isolated_profile_dir
    ):
        # Setup
        profile_path = _seed_oauth_profile(isolated_profile_dir)
        respx.post("https://core.test/o/revoke_token/").mock(
            side_effect=httpx.ConnectError("boom")
        )
        # Action
        result = cli_runner.invoke(_logout_app(), [])
        saved = yaml.safe_load(profile_path.read_text())
        # Expected
        assert result.exit_code == 0
        assert "Could not reach core" in result.output
        assert "--force-remote" in result.output
        assert saved["auth_method"] == AuthHeaderTypeEnum.TOKEN.value


class TestLogoutTokenProfile:
    def test_logout_on_token_only_profile_is_a_noop(
        self, cli_runner, isolated_profile_dir
    ):
        # Setup
        profile_path = _seed_token_profile(isolated_profile_dir)
        profile_before = profile_path.read_text()
        # Action
        result = cli_runner.invoke(_logout_app(), [])
        profile_after = profile_path.read_text()
        # Expected
        assert result.exit_code == 0
        assert "No OAuth session to log out from" in result.output
        assert profile_before == profile_after


class TestLogoutProfileFlag:
    @respx.mock
    def test_profile_flag_only_touches_target_profile(
        self, cli_runner, isolated_profile_dir
    ):
        # Setup
        target_path = _seed_oauth_profile(isolated_profile_dir, name="staging")
        bystander_path = _seed_oauth_profile(
            isolated_profile_dir, name="default", refresh_token="bystander-token"
        )
        bystander_before = bystander_path.read_text()
        respx.post("https://core.test/o/revoke_token/").mock(
            return_value=httpx.Response(200)
        )
        # Action
        result = cli_runner.invoke(_logout_app(), ["--profile", "staging"])
        target_saved = yaml.safe_load(target_path.read_text())
        bystander_after = bystander_path.read_text()
        # Expected
        assert result.exit_code == 0
        assert target_saved["auth_method"] == AuthHeaderTypeEnum.TOKEN.value
        assert bystander_before == bystander_after
