"""Basic import tests for the pages module."""

import unittest


class TestPagesImports(unittest.TestCase):
    """Test that all pages module components can be imported successfully."""

    def test_import_commands(self):
        """Test that commands module can be imported."""
        try:
            from cli.pages import commands

            self.assertIsNotNone(commands)
        except ImportError as e:
            self.fail(f"Failed to import cli.pages.commands: {e}")

    def test_import_executor(self):
        """Test that executor module can be imported."""
        try:
            from cli.pages import executor

            self.assertIsNotNone(executor)
        except ImportError as e:
            self.fail(f"Failed to import cli.pages.executor: {e}")

    def test_import_models(self):
        """Test that models module can be imported."""
        try:
            from cli.pages import models

            self.assertIsNotNone(models)
        except ImportError as e:
            self.fail(f"Failed to import cli.pages.models: {e}")

    def test_import_exceptions(self):
        """Test that exceptions module can be imported."""
        try:
            from cli.pages import exceptions

            self.assertIsNotNone(exceptions)
        except ImportError as e:
            self.fail(f"Failed to import cli.pages.exceptions: {e}")

    def test_import_helpers(self):
        """Test that helpers module can be imported."""
        try:
            from cli.pages import helpers

            self.assertIsNotNone(helpers)
        except ImportError as e:
            self.fail(f"Failed to import cli.pages.helpers: {e}")

    def test_import_pipelines(self):
        """Test that pipelines module can be imported."""
        try:
            from cli.pages import pipelines

            self.assertIsNotNone(pipelines)
        except ImportError as e:
            self.fail(f"Failed to import cli.pages.pipelines: {e}")
