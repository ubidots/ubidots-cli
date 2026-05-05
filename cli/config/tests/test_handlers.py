from unittest import TestCase
from unittest.mock import MagicMock
from unittest.mock import patch

from cli.commons.exceptions import CurrentPlanDoesNotIncludeRuntimes
from cli.config.handlers import get_runtimes
from cli.config.handlers import set_configuration
from cli.config.models import AuthHeaderTypeEnum


class TestGetRuntimes(TestCase):
    @patch("cli.config.handlers.get_runtimes_from_api")
    def test_returns_empty_list_when_plan_has_no_runtimes(self, mock_api):
        mock_api.side_effect = CurrentPlanDoesNotIncludeRuntimes()
        result = get_runtimes("any_token")
        self.assertEqual(result, [])

    @patch("cli.config.handlers.get_runtimes_from_api")
    def test_returns_runtime_labels_from_api_response(self, mock_api):
        mock_api.return_value = [{"label": "python3.10"}, {"label": "nodejs16"}]
        result = get_runtimes("valid_token")
        self.assertEqual(result, ["python3.10", "nodejs16"])


class TestSetConfiguration(TestCase):
    @patch("cli.config.handlers.save_profile_configuration")
    @patch("cli.config.handlers.get_runtimes")
    @patch("cli.config.handlers.validate_auth_method")
    @patch("cli.config.handlers.existing_profile")
    @patch("cli.config.handlers.validate_profile")
    @patch("cli.config.handlers.exists_default_profile")
    @patch("cli.config.handlers.exist_config_file")
    def test_saves_profile_successfully_when_runtimes_is_empty(
        self,
        mock_exist_config,
        mock_exists_default,
        mock_validate_profile,
        mock_existing_profile,
        mock_validate_auth,
        mock_get_runtimes,
        mock_save_config,
    ):
        """STEM plan users (empty runtimes) must be able to save their profile."""
        mock_exist_config.return_value = True
        mock_exists_default.return_value = True
        mock_validate_auth.return_value = AuthHeaderTypeEnum.TOKEN
        mock_get_runtimes.return_value = []
        formatter = MagicMock()

        set_configuration(
            api_domain="https://industrial.api.ubidots.com",
            auth_method_key="TOKEN",
            access_token="stem_token",
            profile="stem-profile",
            formatter=formatter,
        )

        mock_save_config.assert_called_once()
        saved_model = mock_save_config.call_args[1]["config_model"]
        self.assertEqual(saved_model.runtimes, [])
        formatter.emit_success.assert_called_once()
