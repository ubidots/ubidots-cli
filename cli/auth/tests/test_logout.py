import os
from urllib.parse import parse_qs

import httpx
import pytest
import respx
import typer
import yaml
from typer.testing import CliRunner

from cli.auth.commands import logout
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
        "output_format": OutputFormatFieldsEnum.MACHINE.value,
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
        "output_format": OutputFormatFieldsEnum.MACHINE.value,
    }
    profile_path = profiles_dir / f"{name}.yaml"
    profile_path.write_text(yaml.dump(data))
    if os.name != "nt":
        os.chmod(profile_path, 0o600)
    return profile_path


def _expected_cleared_yaml(api_domain="https://core.test"):
    return {
        "api_domain": api_domain,
        "auth_method": AuthHeaderTypeEnum.TOKEN.value,
        "access_token": "",
        "containerRepositoryBase": settings.CONFIG.DEFAULT_CONTAINER_REPOSITORY,
        "runtimes": [],
        "output_format": OutputFormatFieldsEnum.MACHINE.value,
    }


def _expected_revoke_form_body():
    return {"token": "r-token", "client_id": "ubidots-cli"}


class TestLogoutHappyPath:
    @respx.mock
    def test_revoke_200_clears_profile_to_full_token_only_state(
        self, cli_runner, isolated_profile_dir
    ):
        # Setup
        profile_path = _seed_oauth_profile(isolated_profile_dir)
        route = respx.post("https://core.test/o/revoke_token/").mock(
            return_value=httpx.Response(200)
        )
        expected_yaml = _expected_cleared_yaml()
        expected_form = _expected_revoke_form_body()
        # Action
        result = cli_runner.invoke(_logout_app(), [])
        actual_yaml = yaml.safe_load(profile_path.read_text())
        sent_form = {
            k: v[0]
            for k, v in parse_qs(route.calls[0].request.content.decode("utf-8")).items()
        }
        # Expected
        assert result.exit_code == 0
        assert "Logged out (profile: default)." in result.output
        assert actual_yaml == expected_yaml
        assert sent_form == expected_form


class TestLogoutErrorPaths:
    @respx.mock
    def test_revoke_4xx_clears_profile_to_full_token_only_state(
        self, cli_runner, isolated_profile_dir
    ):
        # Setup
        profile_path = _seed_oauth_profile(isolated_profile_dir)
        respx.post("https://core.test/o/revoke_token/").mock(
            return_value=httpx.Response(401, json={"error": "invalid_token"})
        )
        expected_yaml = _expected_cleared_yaml()
        # Action
        result = cli_runner.invoke(_logout_app(), [])
        actual_yaml = yaml.safe_load(profile_path.read_text())
        # Expected
        assert result.exit_code == 0
        assert "Logged out (refresh token was already invalid)." in result.output
        assert actual_yaml == expected_yaml

    @respx.mock
    def test_network_error_clears_profile_and_hints_force_remote(
        self, cli_runner, isolated_profile_dir
    ):
        # Setup
        profile_path = _seed_oauth_profile(isolated_profile_dir)
        respx.post("https://core.test/o/revoke_token/").mock(
            side_effect=httpx.ConnectError("boom")
        )
        expected_yaml = _expected_cleared_yaml()
        expected_output_substrings = [
            "Could not reach core to revoke remotely. Local credentials cleared.",
            "ubidots logout --force-remote",
        ]
        # Action
        result = cli_runner.invoke(_logout_app(), [])
        actual_yaml = yaml.safe_load(profile_path.read_text())
        # Expected
        assert result.exit_code == 0
        for substring in expected_output_substrings:
            assert substring in result.output
        assert actual_yaml == expected_yaml


class TestLogoutTokenProfile:
    def test_logout_on_token_only_profile_is_a_noop(
        self, cli_runner, isolated_profile_dir
    ):
        # Setup
        profile_path = _seed_token_profile(isolated_profile_dir)
        expected_yaml = yaml.safe_load(profile_path.read_text())
        # Action
        result = cli_runner.invoke(_logout_app(), [])
        actual_yaml = yaml.safe_load(profile_path.read_text())
        # Expected
        assert result.exit_code == 0
        assert "No OAuth session to log out from." in result.output
        assert actual_yaml == expected_yaml


class TestLogoutProfileFlag:
    @respx.mock
    def test_profile_flag_clears_target_profile_only_and_keeps_bystander_intact(
        self, cli_runner, isolated_profile_dir
    ):
        # Setup
        target_path = _seed_oauth_profile(isolated_profile_dir, name="staging")
        bystander_path = _seed_oauth_profile(
            isolated_profile_dir, name="default", refresh_token="bystander-token"
        )
        bystander_before = yaml.safe_load(bystander_path.read_text())
        respx.post("https://core.test/o/revoke_token/").mock(
            return_value=httpx.Response(200)
        )
        expected_target_yaml = _expected_cleared_yaml()
        # Action
        result = cli_runner.invoke(_logout_app(), ["--profile", "staging"])
        actual_target_yaml = yaml.safe_load(target_path.read_text())
        bystander_after = yaml.safe_load(bystander_path.read_text())
        # Expected
        assert result.exit_code == 0
        assert "Logged out (profile: staging)." in result.output
        assert actual_target_yaml == expected_target_yaml
        assert bystander_after == bystander_before
