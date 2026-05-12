import os
import time
from urllib.parse import parse_qs

import httpx
import pytest
import respx
import yaml

from cli.auth.token_refresh import ensure_fresh_token
from cli.auth.token_refresh import needs_refresh
from cli.commons.enums import OutputFormatFieldsEnum
from cli.commons.exceptions import CoreUnreachableError
from cli.commons.exceptions import RefreshFailedError
from cli.commons.exceptions import RefreshTokenExpiredError
from cli.config.models import AuthHeaderTypeEnum
from cli.config.models import ProfileConfigModel
from cli.settings import settings


@pytest.fixture
def isolated_profile_dir(tmp_path, monkeypatch):
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    monkeypatch.setattr(settings.CONFIG, "DIRECTORY_PATH", tmp_path)
    monkeypatch.setattr(settings.CONFIG, "PROFILES_PATH", profiles_dir)
    monkeypatch.setattr(settings.CONFIG, "FILE_PATH", tmp_path / "config.yaml")
    return profiles_dir


def _oauth_config(expires_at=None, refresh_token="r-old") -> ProfileConfigModel:
    expires_at = expires_at if expires_at is not None else int(time.time()) + 3600
    return ProfileConfigModel(
        api_domain="https://core.test",
        auth_method=AuthHeaderTypeEnum.OAUTH2,
        access_token="jwt-old",
        refresh_token=refresh_token,
        expires_at=expires_at,
        oauth_client_id="ubidots-cli",
        scope="read write",
        token_type="Bearer",
    )


def _seed_profile(profiles_dir, name, config: ProfileConfigModel):
    path = profiles_dir / f"{name}.yaml"
    path.write_text(yaml.dump(config.to_yaml_serializable_format()))
    if os.name != "nt":
        os.chmod(path, 0o600)
    return path


class TestNeedsRefresh:
    def test_token_profile_never_needs_refresh(self):
        # Setup
        config = ProfileConfigModel(
            auth_method=AuthHeaderTypeEnum.TOKEN, access_token="static"
        )
        # Action
        result = needs_refresh(config)
        # Expected
        assert result is False

    def test_oauth_profile_far_from_expiry_does_not_need_refresh(self, monkeypatch):
        # Setup — exp 60s in the future, leeway 30s → 60-30=30 >= 0 → no refresh
        now = 1_700_000_000
        monkeypatch.setattr(time, "time", lambda: now)
        config = _oauth_config(expires_at=now + 60)
        # Action
        result = needs_refresh(config, leeway_seconds=30)
        # Expected
        assert result is False

    def test_oauth_profile_within_leeway_window_needs_refresh(self, monkeypatch):
        # Setup — exp 20s in the future, leeway 30s → 20-30=-10 < 0 → refresh
        now = 1_700_000_000
        monkeypatch.setattr(time, "time", lambda: now)
        config = _oauth_config(expires_at=now + 20)
        # Action
        result = needs_refresh(config, leeway_seconds=30)
        # Expected
        assert result is True

    def test_oauth_profile_already_expired_needs_refresh(self, monkeypatch):
        # Setup
        now = 1_700_000_000
        monkeypatch.setattr(time, "time", lambda: now)
        config = _oauth_config(expires_at=now - 3600)
        # Action
        result = needs_refresh(config, leeway_seconds=30)
        # Expected
        assert result is True


class TestEnsureFreshTokenHappyPath:
    @respx.mock
    def test_expired_token_is_refreshed_and_full_profile_yaml_is_rewritten(
        self, isolated_profile_dir, monkeypatch
    ):
        # Setup
        now = 1_700_000_000
        monkeypatch.setattr(time, "time", lambda: now)
        original_config = _oauth_config(expires_at=now - 60, refresh_token="r-old")
        _seed_profile(isolated_profile_dir, "default", original_config)
        respx.post("https://core.test/o/token/").mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "jwt-new",
                    "refresh_token": "r-new",
                    "expires_in": 900,
                    "scope": "read write",
                    "token_type": "Bearer",
                },
            )
        )
        expected_yaml = {
            "api_domain": "https://core.test",
            "auth_method": AuthHeaderTypeEnum.OAUTH2.value,
            "access_token": "jwt-new",
            "containerRepositoryBase": settings.CONFIG.DEFAULT_CONTAINER_REPOSITORY,
            "runtimes": [],
            "output_format": OutputFormatFieldsEnum.MACHINE.value,
            "oauth_client_id": "ubidots-cli",
            "refresh_token": "r-new",
            "expires_at": now + 900,
            "scope": "read write",
            "token_type": "Bearer",
        }
        # Action
        refreshed_config = ensure_fresh_token(
            profile_name="default", config=original_config
        )
        actual_yaml = yaml.safe_load(
            (isolated_profile_dir / "default.yaml").read_text()
        )
        # Expected
        assert refreshed_config.access_token == "jwt-new"
        assert refreshed_config.refresh_token == "r-new"
        assert refreshed_config.expires_at == now + 900
        assert actual_yaml == expected_yaml

    @respx.mock
    def test_request_body_contains_refresh_grant_and_credentials(
        self, isolated_profile_dir, monkeypatch
    ):
        # Setup
        now = 1_700_000_000
        monkeypatch.setattr(time, "time", lambda: now)
        original_config = _oauth_config(expires_at=now - 60, refresh_token="r-old")
        _seed_profile(isolated_profile_dir, "default", original_config)
        route = respx.post("https://core.test/o/token/").mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "jwt-new",
                    "refresh_token": "r-new",
                    "expires_in": 900,
                    "token_type": "Bearer",
                },
            )
        )
        expected_form = {
            "grant_type": "refresh_token",
            "refresh_token": "r-old",
            "client_id": "ubidots-cli",
        }
        # Action
        ensure_fresh_token(profile_name="default", config=original_config)
        sent_body = route.calls[0].request.content.decode("utf-8")
        actual_form = {k: v[0] for k, v in parse_qs(sent_body).items()}
        # Expected
        assert actual_form == expected_form


class TestEnsureFreshTokenBypass:
    @respx.mock
    def test_token_profile_returns_config_unchanged_and_makes_no_http_call(
        self, isolated_profile_dir
    ):
        # Setup
        token_config = ProfileConfigModel(
            api_domain="https://core.test",
            auth_method=AuthHeaderTypeEnum.TOKEN,
            access_token="static",
        )
        _seed_profile(isolated_profile_dir, "default", token_config)
        route = respx.post("https://core.test/o/token/").mock(
            return_value=httpx.Response(200, json={})
        )
        # Action
        result = ensure_fresh_token(profile_name="default", config=token_config)
        # Expected
        assert result == token_config
        assert route.call_count == 0

    @respx.mock
    def test_oauth_profile_far_from_expiry_returns_config_unchanged(
        self, isolated_profile_dir, monkeypatch
    ):
        # Setup
        now = 1_700_000_000
        monkeypatch.setattr(time, "time", lambda: now)
        original_config = _oauth_config(expires_at=now + 3600)
        _seed_profile(isolated_profile_dir, "default", original_config)
        route = respx.post("https://core.test/o/token/").mock(
            return_value=httpx.Response(200, json={})
        )
        # Action
        result = ensure_fresh_token(profile_name="default", config=original_config)
        # Expected
        assert result == original_config
        assert route.call_count == 0


class TestEnsureFreshTokenErrorPaths:
    @respx.mock
    def test_invalid_grant_raises_session_expired_and_does_not_clear_profile(
        self, isolated_profile_dir, monkeypatch
    ):
        # Setup
        now = 1_700_000_000
        monkeypatch.setattr(time, "time", lambda: now)
        original_config = _oauth_config(expires_at=now - 60)
        profile_path = _seed_profile(isolated_profile_dir, "default", original_config)
        yaml_before = yaml.safe_load(profile_path.read_text())
        respx.post("https://core.test/o/token/").mock(
            return_value=httpx.Response(
                400,
                json={"error": "invalid_grant", "error_description": "Token revoked"},
            )
        )
        # Action / Expected
        with pytest.raises(RefreshTokenExpiredError):
            ensure_fresh_token(profile_name="default", config=original_config)
        yaml_after = yaml.safe_load(profile_path.read_text())
        assert yaml_after == yaml_before

    @respx.mock
    def test_generic_4xx_raises_refresh_failed_with_error_description(
        self, isolated_profile_dir, monkeypatch
    ):
        # Setup
        now = 1_700_000_000
        monkeypatch.setattr(time, "time", lambda: now)
        original_config = _oauth_config(expires_at=now - 60)
        _seed_profile(isolated_profile_dir, "default", original_config)
        respx.post("https://core.test/o/token/").mock(
            return_value=httpx.Response(
                400,
                json={"error": "invalid_request", "error_description": "missing param"},
            )
        )
        # Action / Expected
        with pytest.raises(RefreshFailedError) as excinfo:
            ensure_fresh_token(profile_name="default", config=original_config)
        assert "missing param" in str(excinfo.value)

    @respx.mock
    def test_network_error_raises_core_unreachable_and_leaves_profile_intact(
        self, isolated_profile_dir, monkeypatch
    ):
        # Setup
        now = 1_700_000_000
        monkeypatch.setattr(time, "time", lambda: now)
        original_config = _oauth_config(expires_at=now - 60)
        profile_path = _seed_profile(isolated_profile_dir, "default", original_config)
        yaml_before = yaml.safe_load(profile_path.read_text())
        respx.post("https://core.test/o/token/").mock(
            side_effect=httpx.ConnectError("boom")
        )
        # Action / Expected
        with pytest.raises(CoreUnreachableError) as excinfo:
            ensure_fresh_token(profile_name="default", config=original_config)
        assert "https://core.test" in str(excinfo.value)
        yaml_after = yaml.safe_load(profile_path.read_text())
        assert yaml_after == yaml_before


class TestEnsureFreshTokenConcurrencyDoubleCheck:
    @respx.mock
    def test_second_caller_reusing_locked_state_reads_disk_and_skips_refresh(
        self, isolated_profile_dir, monkeypatch
    ):
        # Setup — first caller refreshes; the in-memory `original_config` of
        # the second caller is stale. The lock-guarded re-read from disk must
        # detect that the on-disk profile is already fresh and skip the
        # second network call.
        now = 1_700_000_000
        monkeypatch.setattr(time, "time", lambda: now)
        first_config = _oauth_config(expires_at=now - 60)
        _seed_profile(isolated_profile_dir, "default", first_config)
        route = respx.post("https://core.test/o/token/").mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "jwt-new",
                    "refresh_token": "r-new",
                    "expires_in": 900,
                    "token_type": "Bearer",
                    "scope": "read write",
                },
            )
        )
        # Action
        first_refreshed = ensure_fresh_token(
            profile_name="default", config=first_config
        )
        second_attempt_with_stale_in_memory = ensure_fresh_token(
            profile_name="default", config=first_config
        )
        # Expected — exactly one network call; second call returns the
        # freshly-loaded disk state.
        assert route.call_count == 1
        assert first_refreshed.access_token == "jwt-new"
        assert second_attempt_with_stale_in_memory.access_token == "jwt-new"
        assert second_attempt_with_stale_in_memory.expires_at == now + 900
