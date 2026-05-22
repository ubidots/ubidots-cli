import stat
import sys
from pathlib import Path
from unittest import TestCase

import pytest
import yaml

from cli.commons.enums import OutputFormatFieldsEnum
from cli.config.helpers import read_cli_configuration
from cli.config.helpers import save_profile_configuration
from cli.config.helpers import validate_profile_config
from cli.config.models import AuthHeaderTypeEnum
from cli.config.models import ProfileConfigModel
from cli.settings import settings


@pytest.fixture
def isolated_profiles(tmp_path, monkeypatch):
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    monkeypatch.setattr(settings.CONFIG, "PROFILES_PATH", profiles)
    return profiles


class TestAuthHeaderTypeEnum(TestCase):
    def test_oauth2_value_is_authorization_header_name(self):
        # Setup
        expected_value = "Authorization"
        # Action
        actual_value = AuthHeaderTypeEnum.OAUTH2.value
        # Expected
        self.assertEqual(actual_value, expected_value)

    def test_token_value_is_unchanged_x_auth_token_header(self):
        # Setup
        expected_value = "X-Auth-Token"
        # Action
        actual_value = AuthHeaderTypeEnum.TOKEN.value
        # Expected
        self.assertEqual(actual_value, expected_value)

    def test_enum_exposes_exactly_two_members(self):
        # Setup
        expected_members = {"TOKEN", "OAUTH2"}
        # Action
        actual_members = {member.name for member in AuthHeaderTypeEnum}
        # Expected
        self.assertEqual(actual_members, expected_members)


class TestProfileConfigModelDefaults(TestCase):
    def test_default_instance_matches_full_expected_model(self):
        # Setup
        expected_model = ProfileConfigModel(
            api_domain=settings.CONFIG.API_DOMAIN,
            auth_method=AuthHeaderTypeEnum.TOKEN,
            access_token="",
            containerRepositoryBase=settings.CONFIG.DEFAULT_CONTAINER_REPOSITORY,
            runtimes=settings.CONFIG.DEFAULT_RUNTIMES,
            output_format=OutputFormatFieldsEnum.MACHINE,
            oauth_client_id="",
            refresh_token="",
            expires_at=0,
            scope="",
            token_type="Bearer",
        )
        # Action
        actual_model = ProfileConfigModel()
        # Expected
        self.assertEqual(actual_model, expected_model)


class TestProfileConfigModelLegacyLoad(TestCase):
    def test_legacy_dict_loads_into_full_token_model(self):
        # Setup
        legacy_dict = {
            "api_domain": "https://core.test",
            "auth_method": "X-Auth-Token",
            "access_token": "static-token",
            "runtimes": [],
            "containerRepositoryBase": "registry/",
            "output_format": "machine",
        }
        expected_model = ProfileConfigModel(
            api_domain="https://core.test",
            auth_method=AuthHeaderTypeEnum.TOKEN,
            access_token="static-token",
            containerRepositoryBase="registry/",
            runtimes=[],
            output_format=OutputFormatFieldsEnum.MACHINE,
            oauth_client_id="",
            refresh_token="",
            expires_at=0,
            scope="",
            token_type="Bearer",
        )
        # Action
        actual_model = ProfileConfigModel(**legacy_dict)
        # Expected
        self.assertEqual(actual_model, expected_model)


class TestProfileConfigModelOAuthValidation(TestCase):
    def test_oauth_with_all_required_fields_loads_into_full_model(self):
        # Setup
        oauth_dict = {
            "api_domain": "https://core.test",
            "auth_method": AuthHeaderTypeEnum.OAUTH2,
            "access_token": "jwt",
            "refresh_token": "r-token",
            "expires_at": 10,
            "oauth_client_id": "ubidots-cli",
            "scope": "read write",
            "token_type": "Bearer",
        }
        expected_model = ProfileConfigModel(
            api_domain="https://core.test",
            auth_method=AuthHeaderTypeEnum.OAUTH2,
            access_token="jwt",
            containerRepositoryBase=settings.CONFIG.DEFAULT_CONTAINER_REPOSITORY,
            runtimes=settings.CONFIG.DEFAULT_RUNTIMES,
            output_format=OutputFormatFieldsEnum.MACHINE,
            oauth_client_id="ubidots-cli",
            refresh_token="r-token",
            expires_at=10,
            scope="read write",
            token_type="Bearer",
        )
        # Action
        actual_model = ProfileConfigModel(**oauth_dict)
        # Expected
        self.assertEqual(actual_model, expected_model)

    def test_oauth_without_refresh_token_raises_with_field_name_in_message(self):
        # Setup
        invalid_dict = {
            "auth_method": AuthHeaderTypeEnum.OAUTH2,
            "access_token": "jwt",
            "refresh_token": "",
            "expires_at": 10,
            "oauth_client_id": "ubidots-cli",
        }
        expected_substring = "refresh_token"
        # Action / Expected
        with pytest.raises(Exception) as excinfo:
            ProfileConfigModel(**invalid_dict)
        self.assertIn(expected_substring, str(excinfo.value))


class TestProfileConfigSerialization:
    def test_token_profile_serializes_without_oauth_fields(self, isolated_profiles):
        # Setup
        model = ProfileConfigModel(
            auth_method=AuthHeaderTypeEnum.TOKEN,
            access_token="static",
        )
        expected_yaml = {
            "api_domain": settings.CONFIG.API_DOMAIN,
            "auth_method": AuthHeaderTypeEnum.TOKEN.value,
            "access_token": "static",
            "containerRepositoryBase": settings.CONFIG.DEFAULT_CONTAINER_REPOSITORY,
            "runtimes": settings.CONFIG.DEFAULT_RUNTIMES,
            "output_format": OutputFormatFieldsEnum.MACHINE.value,
        }
        # Action
        save_profile_configuration(profile="legacy", config_model=model)
        actual_yaml = yaml.safe_load((isolated_profiles / "legacy.yaml").read_text())
        # Expected
        assert actual_yaml == expected_yaml

    def test_oauth_profile_round_trips_through_yaml_with_all_fields(self, isolated_profiles):
        # Setup
        original_model = ProfileConfigModel(
            api_domain="https://core.test",
            auth_method=AuthHeaderTypeEnum.OAUTH2,
            access_token="jwt",
            refresh_token="r-token",
            expires_at=99,
            oauth_client_id="ubidots-cli",
            scope="read write",
            token_type="Bearer",
        )
        # Action
        save_profile_configuration(profile="oauth", config_model=original_model)
        reloaded_model = read_cli_configuration(profile="oauth")
        # Expected
        assert reloaded_model == original_model


class TestProfileFilePermissions:
    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only")
    def test_saved_profile_file_has_mode_0600(self, isolated_profiles):
        # Setup
        model = ProfileConfigModel(auth_method=AuthHeaderTypeEnum.TOKEN, access_token="x")
        expected_mode = 0o600
        # Action
        save_profile_configuration(profile="modes", config_model=model)
        actual_mode = stat.S_IMODE((isolated_profiles / "modes.yaml").stat().st_mode)
        # Expected
        assert actual_mode == expected_mode

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only")
    def test_permissive_file_is_tightened_on_validate(self, isolated_profiles, recwarn):
        # Setup
        profile_path = isolated_profiles / "wide.yaml"
        profile_path.write_text(
            yaml.dump(
                {
                    "api_domain": "https://core.test",
                    "auth_method": "X-Auth-Token",
                    "access_token": "x",
                    "runtimes": [],
                    "containerRepositoryBase": "registry/",
                    "output_format": "machine",
                }
            )
        )
        Path(profile_path).chmod(0o644)
        expected_mode = 0o600
        # Action
        validate_profile_config(yaml.safe_load(profile_path.read_text()), profile_path)
        actual_mode = stat.S_IMODE(profile_path.stat().st_mode)
        # Expected
        assert actual_mode == expected_mode
        assert any("tightening" in str(w.message) or "0o644" in str(w.message) for w in recwarn.list)


class TestValidateProfileConfigBackwardCompat:
    def test_legacy_token_profile_validates_to_full_token_model(self, tmp_path):
        # Setup
        legacy_dict = {
            "api_domain": "https://core.test",
            "auth_method": "X-Auth-Token",
            "access_token": "static-token",
            "runtimes": [],
            "containerRepositoryBase": "registry/",
            "output_format": "machine",
        }
        expected_model = ProfileConfigModel(
            api_domain="https://core.test",
            auth_method=AuthHeaderTypeEnum.TOKEN,
            access_token="static-token",
            containerRepositoryBase="registry/",
            runtimes=[],
            output_format=OutputFormatFieldsEnum.MACHINE,
        )
        # Action
        actual_model = validate_profile_config(legacy_dict, tmp_path / "p.yaml")
        # Expected
        assert actual_model == expected_model

    def test_oauth_profile_validates_to_full_oauth_model(self, tmp_path):
        # Setup
        oauth_dict = {
            "api_domain": "https://core.test",
            "auth_method": "Authorization",
            "access_token": "jwt",
            "refresh_token": "r-token",
            "expires_at": 10,
            "oauth_client_id": "ubidots-cli",
            "scope": "read write",
            "token_type": "Bearer",
            "runtimes": [],
            "containerRepositoryBase": "registry/",
            "output_format": "machine",
        }
        expected_model = ProfileConfigModel(
            api_domain="https://core.test",
            auth_method=AuthHeaderTypeEnum.OAUTH2,
            access_token="jwt",
            refresh_token="r-token",
            expires_at=10,
            oauth_client_id="ubidots-cli",
            scope="read write",
            token_type="Bearer",
            containerRepositoryBase="registry/",
            runtimes=[],
            output_format=OutputFormatFieldsEnum.MACHINE,
        )
        # Action
        actual_model = validate_profile_config(oauth_dict, tmp_path / "p.yaml")
        # Expected
        assert actual_model == expected_model


class TestYamlFixtures:
    def test_legacy_profile_yaml_fixture_loads_into_token_model(self, tmp_path):
        # Setup
        fixtures = Path(__file__).parent / "fixtures"
        profile_data = yaml.safe_load((fixtures / "legacy_profile.yaml").read_text())
        # Action
        model = validate_profile_config(profile_data, fixtures / "legacy_profile.yaml")
        # Expected
        assert model.auth_method == AuthHeaderTypeEnum.TOKEN
        assert model.oauth_client_id == ""
        assert model.refresh_token == ""
        assert model.expires_at == 0
        assert model.token_type == "Bearer"

    def test_oauth_profile_yaml_fixture_loads_into_oauth_model(self, tmp_path):
        # Setup
        fixtures = Path(__file__).parent / "fixtures"
        profile_data = yaml.safe_load((fixtures / "oauth_profile.yaml").read_text())
        # Action
        model = validate_profile_config(profile_data, fixtures / "oauth_profile.yaml")
        # Expected
        assert model.auth_method == AuthHeaderTypeEnum.OAUTH2
        assert model.oauth_client_id == "ubidots-cli"
        assert model.refresh_token == "refresh-token-value"
        assert model.expires_at == 1893456000
        assert model.token_type == "Bearer"
