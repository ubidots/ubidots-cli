from unittest import TestCase

from typer.testing import CliRunner

from cli.devices.commands import app as device_app
from cli.functions.commands import app as function_app
from cli.main import app as root_app

runner = CliRunner()


class TestMachineHelpOutput(TestCase):
    def test_root_help_is_plain_text(self):
        result = runner.invoke(root_app, ["--help"])
        self.assertEqual(result.exit_code, 0)
        output = result.output
        self.assertIn("Usage:", output)
        self.assertIn("Options:", output)
        self.assertIn("Commands:", output)
        self.assertNotIn("╭", output)
        self.assertNotIn("╰", output)
        self.assertNotIn("│", output)

    def test_group_help_is_plain_text(self):
        result = runner.invoke(function_app, ["--help"])
        self.assertEqual(result.exit_code, 0)
        output = result.output
        self.assertIn("Usage:", output)
        self.assertNotIn("╭", output)
        self.assertNotIn("╰", output)

    def test_group_help_preserves_panels(self):
        result = runner.invoke(function_app, ["--help"])
        output = result.output
        self.assertIn("Cloud Commands:", output)
        self.assertIn("Sync Commands:", output)
        self.assertIn("run", output)
        self.assertIn("push", output)

    def test_leaf_command_help_is_plain_text(self):
        result = runner.invoke(function_app, ["list", "--help"])
        self.assertEqual(result.exit_code, 0)
        output = result.output
        self.assertIn("Usage:", output)
        self.assertIn("Options:", output)
        self.assertIn("--profile", output)
        self.assertIn("--format", output)
        self.assertNotIn("╭", output)

    def test_leaf_command_help_shows_all_options(self):
        result = runner.invoke(device_app, ["list", "--help"])
        output = result.output
        self.assertIn("--fields", output)
        self.assertIn("--filter", output)
        self.assertIn("--sort-by", output)
        self.assertIn("--page-size", output)
        self.assertIn("--page", output)
        self.assertIn("--format", output)
        self.assertIn("--help", output)
