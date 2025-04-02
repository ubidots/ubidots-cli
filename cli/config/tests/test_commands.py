from unittest import TestCase
from unittest.mock import patch

import typer
from typer.testing import CliRunner

from cli.commons.exceptions import InvalidOptionError
from cli.commons.exceptions import NoProfileError
from cli.config.commands import config
from cli.config.models import AuthHeaderTypeEnum

app = typer.Typer()
app.command()(config)

runner = CliRunner()


class TestConfigCommand(TestCase):
    @patch("cli.config.handlers.set_default_profile")
    def test_config_set_default_profile(self, mock_set_default):
        """Test setting a profile as default."""
        result = runner.invoke(app, ["--default", "test_profile"])
        self.assertEqual(result.exit_code, 0)
        mock_set_default.assert_called_once_with(profile="test_profile")

    @patch("cli.config.handlers.set_configuration")
    @patch("cli.config.handlers.get_access_token_configuration")
    @patch("cli.config.commands.custom_prompt")
    def test_config_interactive_creation(
        self, mock_prompt, mock_get_token, mock_set_config
    ):
        """Test interactive profile creation."""
        mock_get_token.return_value = ("original_token_value", "masked_token_value")
        mock_prompt.side_effect = [
            "test_profile",
            "https://example.com",
            "TOKEN",
            "original_token_value",
        ]
        result = runner.invoke(app)
        self.assertEqual(result.exit_code, 0)
        mock_set_config.assert_called_once_with(
            profile="test_profile",
            api_domain="https://example.com",
            auth_method_key="TOKEN",
            access_token="original_token_value",
        )

    @patch("cli.config.handlers.set_configuration")
    def test_config_non_interactive_creation(self, mock_set_config):
        """Test non-interactive profile creation."""
        result = runner.invoke(
            app,
            [
                "--no-interactive",
                "--profile",
                "test_profile",
                "--api-domain",
                "https://example.com",
                "--auth-method",
                "TOKEN",
                "--token",
                "my_access_token",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        mock_set_config.assert_called_once_with(
            profile="test_profile",
            api_domain="https://example.com",
            auth_method_key="TOKEN",
            access_token="my_access_token",
        )

    @patch("cli.config.handlers.validate_profile")  # Mock this instead
    def test_config_non_interactive_missing_profile(self, mock_validate_profile):
        """Test that non-interactive mode fails when --profile is missing."""
        mock_validate_profile.side_effect = NoProfileError()
        result = runner.invoke(
            app,
            [
                "--no-interactive",
                "--api-domain",
                "https://example.com",
                "--auth-method",
                "TOKEN",
                "--token",
                "my_access_token",
            ],
        )
        self.assertEqual(result.exit_code, 1)
        mock_validate_profile.assert_called_once()

    @patch("cli.commons.utils.exit_with_error_message")
    @patch("cli.config.handlers.validate_auth_method")
    def test_config_non_interactive_invalid_auth_method(
        self, mock_validate_auth, mock_exit_with_error
    ):
        """Test that non-interactive mode fails when --auth-method is invalid."""

        # Make validate_auth_method raise an error
        mock_validate_auth.side_effect = InvalidOptionError(
            invalid_option="INVALID_METHOD",
            valid_options=AuthHeaderTypeEnum.TOKEN.name,
            option_name="Authentication Method",
        )

        # Run CLI command with an invalid auth method
        result = runner.invoke(
            app,
            [
                "--no-interactive",
                "--profile",
                "test_profile",
                "--api-domain",
                "https://example.com",
                "--auth-method",
                "INVALID_METHOD",
                "--token",
                "my_access_token",
            ],
        )

        self.assertNotEqual(result.exit_code, 0)
        mock_validate_auth.assert_called_once()

    @patch("cli.config.handlers.get_runtimes")
    def test_config_non_interactive_missing_token(self, mock_get_runtimes):
        """Test that non-interactive mode fails when --token is missing."""

        mock_get_runtimes.return_value = []
        result = runner.invoke(
            app,
            [
                "--no-interactive",
                "--profile",
                "test_profile",
                "--api-domain",
                "https://example.com",
                "--auth-method",
                "TOKEN",
            ],
        )

        # Assertions
        self.assertNotEqual(result.exit_code, 0)
        mock_get_runtimes.assert_not_called()
