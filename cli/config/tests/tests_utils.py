from pathlib import Path
from unittest.mock import mock_open

import pytest
import yaml

from cli.config.helpers import mask_token
from cli.config.helpers import read_cli_configuration
from cli.config.helpers import save_cli_configuration
from cli.config.models import APIConfigModel
from cli.config.models import AuthHeaderTypeEnum
from cli.settings import settings


class TestCliConfigurationUtils:
    @pytest.fixture(autouse=True)
    def setup(self, mocker):
        self.mocker = mocker

    def test_save_cli_configuration(self):
        # Setup
        config_model = APIConfigModel(
            api_domain="https://example.com",
            auth_method=AuthHeaderTypeEnum.TOKEN,
            access_token="123456",
        )
        expected_yaml = yaml.dump(config_model.to_yaml_serializable_format())
        mock_file_open = mock_open()
        self.mocker.patch("builtins.open", mock_file_open, create=True)
        self.mocker.patch.object(Path, "mkdir")
        # Action
        save_cli_configuration(config_model)
        mock_file_open.assert_called_once_with(settings.CONFIG.FILE_PATH, "w")
        written_calls = mock_file_open().write.mock_calls
        written_content = "".join(call.args[0] for call in written_calls)
        # Assert
        assert written_content == expected_yaml

    def test_read_cli_configuration(self):
        # Setup
        config_model = APIConfigModel(
            api_domain="https://example.com",
            auth_method=AuthHeaderTypeEnum.TOKEN,
            access_token="123456",
        )
        expected_yaml = yaml.dump(config_model.to_yaml_serializable_format())
        self.mocker.patch("builtins.open", mock_open(read_data=expected_yaml))
        # Action
        read_config = read_cli_configuration()
        # Assert
        assert read_config == config_model

    def test_mask_token(self):
        # Action
        masked_token = mask_token(token="123456")
        # Assert
        assert masked_token == "**3456"
