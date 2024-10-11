from unittest import TestCase
from unittest.mock import patch

import typer
from typer.testing import CliRunner

from cli.config.commands import config
from cli.config.models import AuthHeaderTypeEnum
from cli.settings import settings

app = typer.Typer()
app.command()(config)

runner = CliRunner()


class TestConfigCommand(TestCase):
    @patch("cli.config.commands.custom_prompt")
    @patch("cli.config.handlers.get_access_token_configuration")
    @patch("cli.config.handlers.set_configuration")
    def test_default_config_input(self, mock_set_config, mock_get_token, mock_prompt):
        # Setup
        mock_get_token.return_value = ("original_token_value", "masked_token_value")
        mock_prompt.side_effect = [
            settings.CONFIG.API_DOMAIN,
            AuthHeaderTypeEnum.TOKEN.name,
            "",
        ]
        # Action
        result = runner.invoke(app)
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_set_config.assert_called_once_with(
            api_domain=settings.CONFIG.API_DOMAIN,
            auth_method_key=AuthHeaderTypeEnum.TOKEN.name,
            access_token="original_token_value",
        )

    @patch("cli.config.commands.custom_prompt")
    @patch("cli.config.handlers.get_access_token_configuration")
    @patch("cli.config.handlers.set_configuration")
    def test_config_valid_input(self, mock_set_config, mock_get_token, mock_prompt):
        # Setup
        mock_get_token.return_value = ("original_token_value", "masked_token_value")
        mock_prompt.side_effect = [
            "https://example.com",
            AuthHeaderTypeEnum.TOKEN.name,
            "new_access_token",
        ]
        # Action
        result = runner.invoke(app)
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_set_config.assert_called_once_with(
            api_domain="https://example.com",
            auth_method_key=AuthHeaderTypeEnum.TOKEN.name,
            access_token="new_access_token",
        )

    @patch("cli.config.commands.custom_prompt")
    @patch("cli.config.handlers.get_access_token_configuration")
    def test_config_invalid_auth_method(self, mock_get_token, mock_prompt):
        # Setup
        mock_get_token.return_value = ("original_token_value", "masked_token_value")
        mock_prompt.side_effect = [
            "https://example.com",
            "INVALID_AUTH_METHOD",
            "new_access_token",
        ]
        # Action
        result = runner.invoke(app)
        # Expected
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn(
            "'INVALID_AUTH_METHOD' is not a valid Authentication Method. "
            "Valid options are: ",
            result.stdout,
        )

    @patch("cli.config.commands.custom_prompt")
    @patch("cli.config.handlers.get_access_token_configuration")
    @patch("cli.config.handlers.set_configuration")
    def test_config_no_token_input(self, mock_set_config, mock_get_token, mock_prompt):
        # Setup
        mock_get_token.return_value = ("original_token_value", "masked_token_value")
        mock_prompt.side_effect = [
            "https://example.com",
            AuthHeaderTypeEnum.TOKEN.name,
            "",
        ]
        # Action
        result = runner.invoke(app)
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_set_config.assert_called_once_with(
            api_domain="https://example.com",
            auth_method_key=AuthHeaderTypeEnum.TOKEN.name,
            access_token="original_token_value",
        )
