from pathlib import Path
from unittest import TestCase
from unittest.mock import mock_open
from unittest.mock import patch

import requests
import yaml

from cli.commons.exceptions import CurrentPlanDoesNotIncludeRuntimes
from cli.commons.exceptions import NoProfileError
from cli.commons.exceptions import ProfileConfigEmptyFieldsError
from cli.commons.exceptions import ProfileConfigMissingFieldsError
from cli.config.helpers import create_config_file
from cli.config.helpers import create_default_profile
from cli.config.helpers import exist_config_file
from cli.config.helpers import exists_default_profile
from cli.config.helpers import extract_profile_paths
from cli.config.helpers import get_active_profile_configuration
from cli.config.helpers import get_profile_configuration
from cli.config.helpers import get_runtimes_from_api
from cli.config.helpers import mask_token
from cli.config.helpers import overwrite_default_profile
from cli.config.helpers import profile_exists
from cli.config.helpers import read_cli_configuration
from cli.config.helpers import save_profile_configuration
from cli.config.helpers import validate_profile
from cli.config.helpers import validate_profile_config
from cli.config.models import AuthHeaderTypeEnum
from cli.config.models import ProfileConfigModel
from cli.settings import settings


class TestCLIConfiguration(TestCase):
    def setUp(self):
        self.profile = "test-profile"
        self.config_directory = Path(settings.CONFIG.DIRECTORY_PATH)
        self.profile_path = self.config_directory / "profiles" / f"{self.profile}.yaml"

    def test_save_cli_configuration(self):
        # Setup
        config_model = ProfileConfigModel(
            api_domain="https://api.example.com",
            auth_method=AuthHeaderTypeEnum.TOKEN,
            access_token="example_token_123",
            runtimes=[],
            containerRepositoryBase=settings.CONFIG.DEFAULT_CONTAINER_REPOSITORY,
        )
        # Action
        save_profile_configuration(profile=self.profile, config_model=config_model)
        # Expected
        with self.profile_path.open() as config_file:
            self.assertEqual(
                yaml.safe_load(config_file), config_model.to_yaml_serializable_format()
            )

    def test_read_cli_configuration(self):
        # Setup
        config_data = {
            "api_domain": "https://api.example.com",
            "auth_method": AuthHeaderTypeEnum.TOKEN.value,
            "access_token": "example_token_123",
            "runtimes": [],
            "containerRepositoryBase": settings.CONFIG.DEFAULT_CONTAINER_REPOSITORY,
        }
        with self.profile_path.open("w") as config_file:
            yaml.dump(config_data, config_file)
        # Action
        config_model = read_cli_configuration(profile=self.profile)
        # Expected
        self.assertIsInstance(config_model, ProfileConfigModel)
        self.assertEqual(config_model.api_domain, config_data["api_domain"])
        self.assertEqual(config_model.auth_method, AuthHeaderTypeEnum.TOKEN)
        self.assertEqual(config_model.access_token, config_data["access_token"])
        self.assertEqual(config_model.runtimes, config_data["runtimes"])
        self.assertEqual(
            config_model.containerRepositoryBase, config_data["containerRepositoryBase"]
        )

    def test_mask_token_with_default_visible_chars(self):
        # Setup
        token = "1234567890"
        expected_result = "******7890"
        # Action
        masked_token = mask_token(token)
        # Expected
        self.assertEqual(masked_token, expected_result)

    def test_mask_token_with_custom_visible_chars(self):
        # Setup
        token = "1234567890"
        visible_chars = 2
        expected_result = "********90"
        # Action
        masked_token = mask_token(token, visible_chars)
        # Expected
        self.assertEqual(masked_token, expected_result)

    def test_mask_token_all_chars_visible_equals_token_length(self):
        # Setup
        token = "1234"
        expected_result = "******1234"
        masked_token = mask_token(token)
        # Expected
        self.assertEqual(masked_token, expected_result)


class TestCLIHelperFunctions(TestCase):
    def setUp(self):
        self.profile = "test-profile"
        self.profile_path = Path(settings.CONFIG.PROFILES_PATH) / f"{self.profile}.yaml"
        self.config_path = Path(settings.CONFIG.FILE_PATH)

    @patch("cli.config.helpers.Path.exists", return_value=True)
    def test_exists_default_profile(self, mock_exists):
        self.assertTrue(exists_default_profile())

    @patch("cli.config.helpers.Path.open", new_callable=mock_open)
    @patch("cli.config.helpers.yaml.dump")
    def test_create_default_profile(self, mock_yaml_dump, mock_file):
        create_default_profile()
        mock_yaml_dump.assert_called_once()

    @patch("cli.config.helpers.Path.exists", return_value=True)
    def test_exist_config_file(self, mock_exists):
        self.assertTrue(exist_config_file())

    @patch("cli.config.helpers.Path.open", new_callable=mock_open)
    @patch("cli.config.helpers.yaml.dump")
    def test_create_config_file(self, mock_yaml_dump, mock_file):
        create_config_file()
        mock_yaml_dump.assert_called_once()

    @patch("cli.config.helpers.exit_with_error_message")
    def test_validate_profile_empty(self, mock_exit):
        validate_profile("")
        mock_exit.assert_called_once()
        self.assertIsInstance(mock_exit.call_args[1]["exception"], NoProfileError)

    @patch(
        "cli.config.helpers.Path.open",
        new_callable=mock_open,
        read_data='{"profile": "test"}',
    )
    @patch("cli.config.helpers.yaml.safe_load", return_value={"profile": "test"})
    @patch("cli.config.helpers.yaml.safe_dump")
    def test_overwrite_default_profile(self, mock_safe_dump, mock_safe_load, mock_file):
        overwrite_default_profile("new-profile")
        mock_safe_dump.assert_called_once()

    @patch("cli.config.helpers.Path.exists", return_value=True)
    @patch(
        "cli.config.helpers.load_yaml",
        return_value={"api_domain": "https://api.example.com"},
    )
    @patch(
        "cli.config.helpers.validate_profile_config",
        return_value=ProfileConfigModel(api_domain="https://api.example.com"),
    )
    def test_get_profile_configuration(
        self, mock_validate, mock_load_yaml, mock_exists
    ):
        profile = "test-profile"
        config = get_profile_configuration(profile)
        self.assertIsInstance(config, ProfileConfigModel)

    @patch("cli.config.helpers.load_yaml")
    @patch(
        "cli.config.helpers.extract_profile_paths",
        return_value=("profiles_path", "test-profile"),
    )
    @patch(
        "cli.config.helpers.validate_profile_config",
        return_value=ProfileConfigModel(api_domain="https://api.example.com"),
    )
    def test_get_active_profile_configuration(
        self, mock_validate, mock_extract, mock_load_yaml
    ):
        config = get_active_profile_configuration()
        self.assertIsInstance(config, ProfileConfigModel)

    @patch("cli.config.helpers.Path.exists", return_value=True)
    def test_profile_exists(self, mock_exists):
        self.assertTrue(profile_exists("test-profile"))

    def test_extract_profile_paths_valid(self):
        config = {"profilesPath": "profiles", "profile": "test-profile"}
        profiles_path, profile = extract_profile_paths(config, Path("config.yaml"))
        self.assertEqual(profiles_path, "profiles")
        self.assertEqual(profile, "test-profile")

    def test_extract_profile_paths_missing(self):
        config = {"profilesPath": "profiles"}
        with self.assertRaises(ValueError):
            extract_profile_paths(config, Path("config.yaml"))

    def test_validate_profile_config_missing_fields(self):
        profile_config = {"api_domain": "https://api.example.com"}
        with self.assertRaises(ProfileConfigMissingFieldsError):
            validate_profile_config(profile_config, Path("test.yaml"))

    def test_validate_profile_config_empty_fields(self):
        profile_config = {
            "api_domain": "",
            "auth_method": "TOKEN",
            "access_token": "token",
            "runtimes": [],  # Ensure it's included, even if empty
            "containerRepositoryBase": "",  # Ensure it's included, even if empty
        }
        with self.assertRaises(ProfileConfigEmptyFieldsError):
            validate_profile_config(profile_config, Path("test.yaml"))

    @patch("cli.config.helpers.requests.get")
    def test_get_runtimes_from_api_success(self, mock_get):
        mock_get.return_value.json.return_value = [{"runtime": "python3.9"}]
        mock_get.return_value.raise_for_status.return_value = None
        runtimes = get_runtimes_from_api("valid_token")
        self.assertEqual(runtimes, [{"runtime": "python3.9"}])

    @patch("cli.config.helpers.exit_with_error_message")
    @patch("cli.config.helpers.requests.get")
    def test_get_runtimes_from_api_payment_required(self, mock_get, mock_exit):
        mock_response = requests.Response()
        mock_response.status_code = 402
        mock_get.return_value = mock_response

        get_runtimes_from_api("invalid_token")

        mock_exit.assert_called_once()
        self.assertIsInstance(
            mock_exit.call_args[1]["exception"], CurrentPlanDoesNotIncludeRuntimes
        )

    @patch("cli.config.helpers.requests.get")
    def test_get_runtimes_from_api_invalid_response(self, mock_get):
        mock_get.return_value.json.return_value = {"error": "unexpected format"}
        mock_get.return_value.raise_for_status.return_value = None
        self.assertEqual(get_runtimes_from_api("valid_token"), [])
