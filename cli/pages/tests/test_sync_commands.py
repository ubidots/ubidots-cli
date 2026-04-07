import unittest
from unittest.mock import ANY
from unittest.mock import patch

from typer.testing import CliRunner

from cli.pages.commands import app


@patch("cli.pages.commands.executor.push_page_to_cloud_platform")
class TestPushCommand(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def test_push_default(self, mock_push_page):
        result = self.runner.invoke(app, ["push"])

        self.assertEqual(result.exit_code, 0)
        mock_push_page.assert_called_once_with(
            confirm=False,
            profile="",
            verbose=False,
            formatter=ANY,
        )

    def test_push_with_yes_flag(self, mock_push_page):
        result = self.runner.invoke(app, ["push", "--yes"])

        self.assertEqual(result.exit_code, 0)
        mock_push_page.assert_called_once_with(
            confirm=True,
            profile="",
            verbose=False,
            formatter=ANY,
        )

    def test_push_with_profile(self, mock_push_page):
        result = self.runner.invoke(app, ["push", "--profile", "production"])

        self.assertEqual(result.exit_code, 0)
        mock_push_page.assert_called_once_with(
            confirm=False,
            profile="production",
            verbose=False,
            formatter=ANY,
        )


@patch("cli.pages.commands.executor.pull_page_from_cloud_platform")
class TestPullCommand(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def test_pull_with_remote_id(self, mock_pull_page_cloud):
        result = self.runner.invoke(
            app, ["pull", "--remote-id", "abc123def456789012345678"]
        )

        self.assertEqual(result.exit_code, 0)
        mock_pull_page_cloud.assert_called_once_with(
            remote_id="abc123def456789012345678",
            profile="",
            verbose=False,
            confirm=False,
            formatter=ANY,
        )

    def test_pull_without_remote_id(self, mock_pull_page_cloud):
        result = self.runner.invoke(app, ["pull"])

        self.assertEqual(result.exit_code, 0)
        mock_pull_page_cloud.assert_called_once_with(
            remote_id="",
            profile="",
            verbose=False,
            confirm=False,
            formatter=ANY,
        )

    def test_pull_with_yes_flag(self, mock_pull_page_cloud):
        result = self.runner.invoke(app, ["pull", "--yes"])

        self.assertEqual(result.exit_code, 0)
        mock_pull_page_cloud.assert_called_once_with(
            remote_id="",
            profile="",
            verbose=False,
            confirm=True,
            formatter=ANY,
        )

    def test_pull_with_profile(self, mock_pull_page_cloud):
        result = self.runner.invoke(app, ["pull", "--profile", "staging"])

        self.assertEqual(result.exit_code, 0)
        mock_pull_page_cloud.assert_called_once_with(
            remote_id="",
            profile="staging",
            verbose=False,
            confirm=False,
            formatter=ANY,
        )


class TestCloudCommandsIntegration(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def test_app_help_shows_cloud_commands(self):
        result = self.runner.invoke(app, ["--help"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Cloud Commands", result.stdout)

    def test_app_help_shows_sync_commands(self):
        result = self.runner.invoke(app, ["--help"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Sync Commands", result.stdout)

    def test_add_command_help(self):
        result = self.runner.invoke(app, ["add", "--help"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("NAME", result.stdout)
        self.assertIn("--profile", result.stdout)
        self.assertIn("--label", result.stdout)

    def test_get_command_help(self):
        result = self.runner.invoke(app, ["get", "--help"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("--id", result.stdout)
        self.assertIn("--label", result.stdout)
        self.assertIn("--fields", result.stdout)
        self.assertIn("--format", result.stdout)

    def test_delete_command_help(self):
        result = self.runner.invoke(app, ["delete", "--help"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("--id", result.stdout)
        self.assertIn("--label", result.stdout)
        self.assertIn("--yes", result.stdout)

    def test_push_command_help(self):
        result = self.runner.invoke(app, ["push", "--help"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Update and synchronize your local page code", result.stdout)

    def test_pull_command_help(self):
        result = self.runner.invoke(app, ["pull", "--help"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Retrieve and update your local page code", result.stdout)
