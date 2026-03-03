import unittest
from unittest.mock import patch

from typer.testing import CliRunner

from cli.pages.commands import app
from cli.pages.models import PageTypeEnum


class TestDevAddCommand(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    @patch("cli.pages.commands.executor.create_page")
    def test_dev_add_command_default_values(self, mock_create_page):
        result = self.runner.invoke(app, ["dev", "add"])

        self.assertEqual(result.exit_code, 0)
        mock_create_page.assert_called_once_with(
            name="my_page",
            verbose=False,
            profile="",
            type=PageTypeEnum.DASHBOARD,
        )

    @patch("cli.pages.commands.executor.create_page")
    def test_init_command_with_name(self, mock_create_page):
        result = self.runner.invoke(app, ["dev", "add", "--name", "test_page"])

        self.assertEqual(result.exit_code, 0)
        mock_create_page.assert_called_once_with(
            name="test_page", verbose=False, profile="", type=PageTypeEnum.DASHBOARD
        )

    @patch("cli.pages.commands.executor.create_page")
    def test_init_command_with_profile(self, mock_create_page):
        result = self.runner.invoke(app, ["dev", "add", "--profile", "prod"])

        self.assertEqual(result.exit_code, 0)
        mock_create_page.assert_called_once_with(
            name="my_page", verbose=False, profile="prod", type=PageTypeEnum.DASHBOARD
        )

    @patch("cli.pages.commands.executor.create_page")
    def test_init_command_with_type(self, mock_create_page):
        result = self.runner.invoke(app, ["dev", "add", "--type", "dashboard"])

        self.assertEqual(result.exit_code, 0)
        mock_create_page.assert_called_once_with(
            name="my_page", verbose=False, profile="", type=PageTypeEnum.DASHBOARD
        )

    @patch("cli.pages.commands.executor.create_page")
    def test_init_command_verbose(self, mock_create_page):
        result = self.runner.invoke(app, ["dev", "add", "--verbose"])

        self.assertEqual(result.exit_code, 0)
        mock_create_page.assert_called_once_with(
            name="my_page", verbose=True, profile="", type=PageTypeEnum.DASHBOARD
        )

    @patch("cli.pages.commands.executor.create_page")
    def test_init_command_all_options(self, mock_create_page):
        result = self.runner.invoke(
            app,
            [
                "dev",
                "add",
                "--name",
                "custom_page",
                "--profile",
                "staging",
                "--type",
                "dashboard",
                "--verbose",
            ],
        )

        self.assertEqual(result.exit_code, 0)
        mock_create_page.assert_called_once_with(
            name="custom_page",
            verbose=True,
            profile="staging",
            type=PageTypeEnum.DASHBOARD,
        )

    def test_init_command_with_remote_id(self):
        result = self.runner.invoke(app, ["dev", "add", "--remote-id", "page123"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("not implemented yet", result.stdout.lower())


class TestStartCommand(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    @patch("cli.pages.commands.executor.start_page")
    def test_start_command_default(self, mock_start_page):
        result = self.runner.invoke(app, ["dev", "start"])

        self.assertEqual(result.exit_code, 0)
        mock_start_page.assert_called_once_with(verbose=False)

    @patch("cli.pages.commands.executor.start_page")
    def test_start_command_verbose(self, mock_start_page):
        result = self.runner.invoke(app, ["dev", "start", "--verbose"])

        self.assertEqual(result.exit_code, 0)
        mock_start_page.assert_called_once_with(verbose=True)


class TestStopCommand(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    @patch("cli.pages.commands.executor.stop_page")
    def test_stop_command_default(self, mock_stop_page):
        result = self.runner.invoke(app, ["dev", "stop"])

        self.assertEqual(result.exit_code, 0)
        mock_stop_page.assert_called_once_with(verbose=False)

    @patch("cli.pages.commands.executor.stop_page")
    def test_stop_command_verbose(self, mock_stop_page):
        result = self.runner.invoke(app, ["dev", "stop", "--verbose"])

        self.assertEqual(result.exit_code, 0)
        mock_stop_page.assert_called_once_with(verbose=True)


class TestRestartCommand(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    @patch("cli.pages.commands.executor.restart_page")
    def test_restart_command_default(self, mock_restart_page):
        result = self.runner.invoke(app, ["dev", "restart"])

        self.assertEqual(result.exit_code, 0)
        mock_restart_page.assert_called_once_with(verbose=False)

    @patch("cli.pages.commands.executor.restart_page")
    def test_restart_command_verbose(self, mock_restart_page):
        result = self.runner.invoke(app, ["dev", "restart", "--verbose"])

        self.assertEqual(result.exit_code, 0)
        mock_restart_page.assert_called_once_with(verbose=True)


class TestStatusCommand(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    @patch("cli.pages.commands.executor.status_page")
    def test_status_command_default(self, mock_status_page):
        result = self.runner.invoke(app, ["dev", "status"])

        self.assertEqual(result.exit_code, 0)
        mock_status_page.assert_called_once_with(verbose=False)

    @patch("cli.pages.commands.executor.status_page")
    def test_status_command_verbose(self, mock_status_page):
        result = self.runner.invoke(app, ["dev", "status", "--verbose"])

        self.assertEqual(result.exit_code, 0)
        mock_status_page.assert_called_once_with(verbose=True)


class TestListCommand(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    @patch("cli.pages.commands.executor.list_pages")
    def test_list_command_default(self, mock_list_pages):
        result = self.runner.invoke(app, ["dev", "list"])

        self.assertEqual(result.exit_code, 0)
        mock_list_pages.assert_called_once_with(verbose=False)

    @patch("cli.pages.commands.executor.list_pages")
    def test_list_command_verbose(self, mock_list_pages):
        result = self.runner.invoke(app, ["dev", "list", "--verbose"])

        self.assertEqual(result.exit_code, 0)
        mock_list_pages.assert_called_once_with(verbose=True)


class TestCommandsIntegration(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def test_app_help(self):
        result = self.runner.invoke(app, ["--help"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Tool for managing and developing Ubidots Pages", result.stdout)

    def test_init_command_help(self):
        result = self.runner.invoke(app, ["dev", "add", "--help"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Create a new local Ubidots page", result.stdout)

    def test_start_command_help(self):
        result = self.runner.invoke(app, ["dev", "start", "--help"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Start the local development server", result.stdout)

    def test_stop_command_help(self):
        result = self.runner.invoke(app, ["dev", "stop", "--help"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Stop the local development server", result.stdout)

    def test_restart_command_help(self):
        result = self.runner.invoke(app, ["dev", "restart", "--help"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Restart the local development server", result.stdout)

    def test_status_command_help(self):
        result = self.runner.invoke(app, ["dev", "status", "--help"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Show the status of the local development server", result.stdout)

    def test_list_command_help(self):
        result = self.runner.invoke(app, ["dev", "list", "--help"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("List all pages and their status", result.stdout)


if __name__ == "__main__":
    unittest.main()
