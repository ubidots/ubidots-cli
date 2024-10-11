from unittest import TestCase

import yaml

from cli.config.helpers import mask_token
from cli.config.helpers import read_cli_configuration
from cli.config.helpers import save_cli_configuration
from cli.config.models import APIConfigModel
from cli.config.models import AuthHeaderTypeEnum
from cli.settings import settings


class TestCLIConfiguration(TestCase):
    def setUp(self):
        self.config_directory = settings.CONFIG.DIRECTORY_PATH
        self.config_file = settings.CONFIG.FILE_PATH

    def test_save_cli_configuration(self):
        # Setup
        config_model = APIConfigModel(
            api_domain="https://api.example.com",
            auth_method=AuthHeaderTypeEnum.TOKEN,
            access_token="example_token_123",
        )
        # Action
        save_cli_configuration(config_model)
        # Expected
        with self.config_file.open() as config_file:
            self.assertEqual(
                yaml.safe_load(config_file), config_model.to_yaml_serializable_format()
            )

    def test_read_cli_configuration(self):
        # Setup
        config_data = {
            "api_domain": "https://api.example.com",
            "auth_method": AuthHeaderTypeEnum.TOKEN.value,
            "access_token": "example_token_123",
        }
        with self.config_file.open("w") as config_file:
            yaml.dump(config_data, config_file)
        # Action
        config_model = read_cli_configuration()
        # Expected
        self.assertIsInstance(config_model, APIConfigModel)
        self.assertEqual(config_model.api_domain, config_data["api_domain"])
        self.assertEqual(config_model.auth_method, AuthHeaderTypeEnum.TOKEN)
        self.assertEqual(config_model.access_token, config_data["access_token"])

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
