"""Tests for the pages engines manager module."""

import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

from docker.errors import DockerException

from cli.pages.engines.enums import PageEngineTypeEnum
from cli.pages.engines.manager import PageEngineClientManager


class TestPageEngineClientManager(unittest.TestCase):
    """Test PageEngineClientManager class."""

    @patch("cli.pages.engines.manager.DockerClient")
    @patch("cli.pages.engines.manager.PageDockerClient")
    def test_get_client_docker_success(
        self, mock_page_docker_client, mock_docker_client
    ):
        """Test getting Docker client successfully."""
        mock_docker_instance = MagicMock()
        mock_docker_client.return_value = mock_docker_instance

        mock_page_client_instance = MagicMock()
        mock_page_docker_client.return_value = mock_page_client_instance

        manager = PageEngineClientManager(engine=PageEngineTypeEnum.DOCKER)
        result = manager.get_client()

        self.assertEqual(result, mock_page_client_instance)
        mock_docker_client.assert_called_once()
        mock_page_docker_client.assert_called_once_with(
            client=mock_docker_instance, engine=PageEngineTypeEnum.DOCKER
        )

    @patch("cli.pages.engines.manager.DockerClient")
    @patch("cli.pages.engines.manager.exit_with_error_message")
    def test_get_client_docker_exception(
        self, mock_exit_with_error, mock_docker_client
    ):
        """Test getting Docker client when DockerException occurs."""
        mock_docker_client.side_effect = DockerException("Docker not available")
        mock_exit_with_error.side_effect = SystemExit(1)  # Simulate program exit

        manager = PageEngineClientManager(engine=PageEngineTypeEnum.DOCKER)

        with self.assertRaises(SystemExit):
            manager.get_client()

        mock_exit_with_error.assert_called_once()

    @patch("cli.pages.engines.manager.DockerClient")
    @patch("cli.pages.engines.manager.exit_with_error_message")
    def test_get_client_docker_permission_error(
        self, mock_exit_with_error, mock_docker_client
    ):
        """Test getting Docker client when PermissionError occurs."""
        mock_docker_client.side_effect = PermissionError("Permission denied")
        mock_exit_with_error.side_effect = SystemExit(1)  # Simulate program exit

        manager = PageEngineClientManager(engine=PageEngineTypeEnum.DOCKER)

        with self.assertRaises(SystemExit):
            manager.get_client()

        mock_exit_with_error.assert_called_once()

    def test_get_client_unsupported_engine(self):
        """Test getting client with unsupported engine type."""
        # Create a mock engine type that's not supported
        unsupported_engine = "UNSUPPORTED"

        manager = PageEngineClientManager(engine=unsupported_engine)

        with self.assertRaises(ValueError) as context:
            manager.get_client()

        self.assertIn("Unsupported engine type", str(context.exception))
