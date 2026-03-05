"""Tests for the pages helpers module."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock, mock_open

from cli.pages.helpers import save_page_manifest
from cli.pages.helpers import read_page_manifest
from cli.pages.helpers import create_and_save_page_manifest
from cli.pages.helpers import get_page_container
from cli.pages.helpers import is_container_running
from cli.pages.helpers import extract_port_from_container
from cli.pages.helpers import generate_page_url
from cli.pages.models import (
    PageTypeEnum,
    PageProjectMetadata,
    PageProjectModel,
    PageModel,
)


class TestManifestHelpers(unittest.TestCase):
    """Test manifest-related helper functions."""

    def test_save_page_manifest_success(self):
        """Test saving page manifest to file."""
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create test metadata
            project_model = PageProjectModel(
                name="test_page",
                label="test_page",
                createdAt="2025-01-01T00:00:00",
                type=PageTypeEnum.DASHBOARD,
            )
            page_model = PageModel(id="page123", label="test_page", name="test_page")
            metadata = PageProjectMetadata(project=project_model, page=page_model)

            # Save manifest
            save_page_manifest(project_path, metadata)

            # Verify file was created
            manifest_file = project_path / ".manifest.yaml"
            self.assertTrue(manifest_file.exists())

    def test_read_page_manifest_success(self):
        """Test reading page manifest from file."""
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create and save test metadata first
            project_model = PageProjectModel(
                name="test_page",
                label="test_page",
                createdAt="2025-01-01T00:00:00",
                type=PageTypeEnum.DASHBOARD,
            )
            page_model = PageModel(id="page123", label="test_page", name="test_page")
            metadata = PageProjectMetadata(project=project_model, page=page_model)
            save_page_manifest(project_path, metadata)

            # Read it back
            read_metadata = read_page_manifest(project_path)

            # Verify data matches
            self.assertEqual(read_metadata.project.name, "test_page")
            self.assertEqual(read_metadata.page.id, "page123")

    def test_read_page_manifest_missing_file(self):
        """Test reading page manifest when file doesn't exist."""
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            with self.assertRaises(FileNotFoundError):
                read_page_manifest(project_path)

    def test_create_and_save_page_manifest_success(self):
        """Test creating and saving page manifest."""
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            metadata = create_and_save_page_manifest(
                project_path=project_path,
                page_name="test_page",
                page_type=PageTypeEnum.DASHBOARD,
                page_id="page123",
            )

            # Verify metadata was created correctly
            self.assertEqual(metadata.project.name, "test_page")
            self.assertEqual(metadata.page.id, "page123")
            self.assertEqual(metadata.project.type, PageTypeEnum.DASHBOARD)

            # Verify file was saved
            manifest_file = project_path / ".manifest.yaml"
            self.assertTrue(manifest_file.exists())


class TestTemplateHelpers(unittest.TestCase):
    """Test template rendering helper functions."""

    def test_template_library_helper_class(self):
        """Test the _TemplateLibrary helper class."""
        from cli.pages.helpers import _TemplateLibrary

        data = {"src": "http://example.com/lib.js", "type": "text/javascript"}
        lib = _TemplateLibrary(data)

        self.assertEqual(
            lib.items,
            [("src", "http://example.com/lib.js"), ("type", "text/javascript")],
        )

    # Note: Template rendering tests are skipped because they require complex settings mocking
    # that would need the actual settings structure. These functions are tested indirectly
    # through integration tests.


class TestContainerHelpers(unittest.TestCase):
    """Test container-related helper functions."""

    def test_get_page_container_success(self):
        """Test getting page container when it exists."""
        mock_container_manager = MagicMock()
        mock_container = MagicMock()
        mock_container_manager.get.return_value = mock_container

        result = get_page_container(mock_container_manager, "test_page")

        self.assertEqual(result, mock_container)
        mock_container_manager.get.assert_called_once_with("page-test_page")

    def test_get_page_container_not_found(self):
        """Test getting page container when it doesn't exist."""
        mock_container_manager = MagicMock()
        mock_container_manager.get.return_value = None

        result = get_page_container(mock_container_manager, "test_page")

        self.assertIsNone(result)

    def test_is_container_running_true(self):
        """Test checking if container is running when it is."""
        mock_container = MagicMock()
        mock_container.status = "running"

        result = is_container_running(mock_container)

        self.assertTrue(result)

    def test_is_container_running_false(self):
        """Test checking if container is running when it's not."""
        mock_container = MagicMock()
        mock_container.status = "exited"

        result = is_container_running(mock_container)

        self.assertFalse(result)

    def test_is_container_running_none_container(self):
        """Test checking if container is running when container is None."""
        result = is_container_running(None)

        self.assertFalse(result)

    def test_extract_port_from_container_success(self):
        """Test extracting port from container when ports exist."""
        mock_container = MagicMock()
        mock_container.ports = {"8090/tcp": [{"HostPort": "8091"}]}

        result = extract_port_from_container(mock_container)

        self.assertEqual(result, "8091")

    def test_extract_port_from_container_no_ports(self):
        """Test extracting port from container when no ports exist."""
        mock_container = MagicMock()
        mock_container.ports = {}

        result = extract_port_from_container(mock_container)

        self.assertIsNone(result)

    def test_extract_port_from_container_none_container(self):
        """Test extracting port from None container."""
        result = extract_port_from_container(None)

        self.assertIsNone(result)


class TestUrlHelpers(unittest.TestCase):
    """Test URL generation helper functions."""

    @patch("cli.pages.engines.settings.page_engine_settings")
    def test_generate_page_url_subdomain_mode(self, mock_settings):
        """Test generating page URL in subdomain mode."""
        mock_settings.CONTAINER.FLASK_MANAGER.EXTERNAL_PORT = 8044

        result = generate_page_url("test_page", "subdomain")

        self.assertEqual(result, "http://test_page.localhost:8044/")

    @patch("cli.pages.engines.settings.page_engine_settings")
    def test_generate_page_url_path_mode(self, mock_settings):
        """Test generating page URL in path mode."""
        mock_settings.CONTAINER.FLASK_MANAGER.EXTERNAL_PORT = 8044

        result = generate_page_url("test_page", "path")

        self.assertEqual(result, "http://localhost:8044/test_page")

    @patch("cli.pages.helpers.extract_port_from_container")
    def test_generate_page_url_port_mode(self, mock_extract_port):
        """Test generating page URL in port mode."""
        mock_container = MagicMock()
        mock_extract_port.return_value = "8091"

        result = generate_page_url("test_page", "port", mock_container)

        self.assertEqual(result, "http://localhost:8091/")

    @patch("cli.pages.helpers.extract_port_from_container")
    def test_generate_page_url_port_mode_no_port(self, mock_extract_port):
        """Test generating page URL in port mode when no port is found."""
        mock_container = MagicMock()
        mock_extract_port.return_value = None

        result = generate_page_url("test_page", "port", mock_container)

        self.assertEqual(result, "http://localhost:8090/")

    def test_generate_page_url_invalid_mode(self):
        """Test generating page URL with invalid routing mode."""
        result = generate_page_url("test_page", "invalid_mode")

        self.assertEqual(result, "")
