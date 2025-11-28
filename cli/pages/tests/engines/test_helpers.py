"""Tests for the pages engines helpers module."""

import unittest
from unittest.mock import patch, MagicMock

from cli.pages.engines.helpers import get_or_create_pages_network
from cli.pages.engines.helpers import build_pages_image_if_needed


class TestNetworkHelpers(unittest.TestCase):
    """Test network-related helper functions."""

    def test_get_or_create_pages_network_exists(self):
        """Test getting existing pages network."""
        mock_client = MagicMock()
        mock_network_manager = MagicMock()
        mock_network = MagicMock()

        mock_client.get_network_manager.return_value = mock_network_manager
        mock_network_manager.list.return_value = [mock_network]

        result = get_or_create_pages_network(mock_client)

        self.assertEqual(result, mock_network)
        mock_network_manager.list.assert_called_once()
        mock_network_manager.create.assert_not_called()

    def test_get_or_create_pages_network_create_new(self):
        """Test creating new pages network when none exists."""
        mock_client = MagicMock()
        mock_network_manager = MagicMock()
        mock_new_network = MagicMock()

        mock_client.get_network_manager.return_value = mock_network_manager
        mock_network_manager.list.return_value = []  # No existing networks
        mock_network_manager.create.return_value = mock_new_network

        result = get_or_create_pages_network(mock_client)

        self.assertEqual(result, mock_new_network)
        mock_network_manager.list.assert_called_once()
        mock_network_manager.create.assert_called_once()


class TestImageHelpers(unittest.TestCase):
    """Test image-related helper functions."""

    @patch("subprocess.run")
    @patch("sys.executable", "/usr/bin/python")
    @patch("pathlib.Path.exists")
    def test_build_pages_image_if_needed_success(
        self, mock_exists, mock_subprocess_run
    ):
        """Test building pages image successfully."""
        mock_exists.return_value = True
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        result = build_pages_image_if_needed()

        self.assertTrue(result)
        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]
        self.assertEqual(args[0], "/usr/bin/python")
        self.assertTrue(args[1].endswith("build_image.py"))

    @patch("pathlib.Path.exists")
    def test_build_pages_image_if_needed_script_not_found(self, mock_exists):
        """Test building pages image when build script doesn't exist."""
        mock_exists.return_value = False

        result = build_pages_image_if_needed()

        self.assertFalse(result)

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_build_pages_image_if_needed_subprocess_error(
        self, mock_exists, mock_subprocess_run
    ):
        """Test building pages image when subprocess fails."""
        mock_exists.return_value = True
        mock_subprocess_run.side_effect = Exception("Build failed")

        result = build_pages_image_if_needed()

        self.assertFalse(result)

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_build_pages_image_if_needed_subprocess_check_error(
        self, mock_exists, mock_subprocess_run
    ):
        """Test building pages image when subprocess check fails."""
        import subprocess

        mock_exists.return_value = True
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, "cmd")

        result = build_pages_image_if_needed()

        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
