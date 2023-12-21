from pathlib import Path
from unittest.mock import mock_open

import pytest
import yaml

from cli import settings
from cli.config.models import APIConfigModel, AuthHeaderType
from cli.config.utils import read_cli_configuration, save_cli_configuration


class TestCliConfigurationUtils:
    @pytest.fixture(autouse=True)
    def setup(self, mocker):
        self.mocker = mocker

    def test_save_cli_configuration(self):
        # Setup
        config_model = APIConfigModel(
            api_domain="https://example.com",
            auth_method=AuthHeaderType.TOKEN,
            access_token="123456",
        )
        expected_yaml = yaml.dump(config_model.for_yaml_dump())
        mock_file_open = mock_open()
        self.mocker.patch("builtins.open", mock_file_open, create=True)
        self.mocker.patch.object(Path, "mkdir")
        # Action
        save_cli_configuration(config_model)
        mock_file_open.assert_called_once_with(settings.UBIDOTS_ACCESS_CONFIG_FILE, "w")
        written_calls = mock_file_open().write.mock_calls
        written_content = "".join(call.args[0] for call in written_calls)
        # Assert
        assert written_content == expected_yaml

    def test_read_cli_configuration(self):
        # Setup
        config_model = APIConfigModel(
            api_domain="https://example.com",
            auth_method=AuthHeaderType.TOKEN,
            access_token="123456",
        )
        expected_yaml = yaml.dump(config_model.for_yaml_dump())
        self.mocker.patch("builtins.open", mock_open(read_data=expected_yaml))
        # Action
        read_config = read_cli_configuration()
        # Assert
        assert read_config == config_model
