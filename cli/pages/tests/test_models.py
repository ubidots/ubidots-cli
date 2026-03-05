"""Tests for the pages models module."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from cli.pages.models import DashboardPageModel
from cli.pages.models import PageModel
from cli.pages.models import PageModelFactory
from cli.pages.models import PageProjectMetadata
from cli.pages.models import PageProjectModel
from cli.pages.models import PageTypeEnum


class TestPageTypeEnum(unittest.TestCase):
    """Test PageTypeEnum values and behavior."""

    def test_page_type_enum_values(self):
        """Test that PageTypeEnum has expected values."""
        self.assertEqual(PageTypeEnum.DASHBOARD, "dashboard")
        self.assertEqual(str(PageTypeEnum.DASHBOARD), "dashboard")

    def test_page_type_enum_membership(self):
        """Test PageTypeEnum membership."""
        self.assertIn(PageTypeEnum.DASHBOARD, PageTypeEnum)
        self.assertEqual(len(PageTypeEnum), 1)  # Only dashboard type currently


class TestPageProjectModel(unittest.TestCase):
    """Test PageProjectModel creation and validation."""

    def test_page_project_model_creation(self):
        """Test creating a PageProjectModel with valid data."""
        model = PageProjectModel(
            name="test_page",
            label="test_page",
            createdAt="2025-01-01T00:00:00",
            type=PageTypeEnum.DASHBOARD,
        )
        self.assertEqual(model.name, "test_page")
        self.assertEqual(model.label, "test_page")
        self.assertEqual(model.createdAt, "2025-01-01T00:00:00")
        self.assertEqual(model.type, PageTypeEnum.DASHBOARD)

    def test_page_project_model_yaml_dump(self):
        """Test that PageProjectModel can be dumped to YAML format."""
        model = PageProjectModel(
            name="test_page",
            label="test_page",
            createdAt="2025-01-01T00:00:00",
            type=PageTypeEnum.DASHBOARD,
        )
        yaml_data = model.to_yaml_serializable_format()
        self.assertIsInstance(yaml_data, dict)
        self.assertEqual(yaml_data["name"], "test_page")
        self.assertEqual(yaml_data["type"], "dashboard")


class TestPageModel(unittest.TestCase):
    """Test PageModel creation and validation."""

    def test_page_model_creation(self):
        """Test creating a PageModel with valid data."""
        model = PageModel(id="page123", label="test_page", name="test_page")
        self.assertEqual(model.id, "page123")
        self.assertEqual(model.label, "test_page")
        self.assertEqual(model.name, "test_page")

    def test_page_model_creation_with_defaults(self):
        """Test creating a PageModel with default id."""
        model = PageModel(label="test_page", name="test_page")
        self.assertEqual(model.id, "")  # Default empty string
        self.assertEqual(model.label, "test_page")
        self.assertEqual(model.name, "test_page")


class TestPageProjectMetadata(unittest.TestCase):
    """Test PageProjectMetadata creation and validation."""

    def test_page_project_metadata_creation(self):
        """Test creating PageProjectMetadata with valid data."""
        project_model = PageProjectModel(
            name="test_page",
            label="test_page",
            createdAt="2025-01-01T00:00:00",
            type=PageTypeEnum.DASHBOARD,
        )
        page_model = PageModel(id="page123", label="test_page", name="test_page")
        metadata = PageProjectMetadata(project=project_model, page=page_model)
        self.assertEqual(metadata.project.name, "test_page")
        self.assertEqual(metadata.page.id, "page123")

    def test_page_project_metadata_yaml_dump(self):
        """Test that PageProjectMetadata can be dumped to YAML format."""
        project_model = PageProjectModel(
            name="test_page",
            label="test_page",
            createdAt="2025-01-01T00:00:00",
            type=PageTypeEnum.DASHBOARD,
        )
        page_model = PageModel(id="page123", label="test_page", name="test_page")
        metadata = PageProjectMetadata(project=project_model, page=page_model)
        yaml_data = metadata.to_yaml_serializable_format()
        self.assertIsInstance(yaml_data, dict)
        self.assertIn("project", yaml_data)
        self.assertIn("page", yaml_data)


class TestDashboardPageModel(unittest.TestCase):
    """Test DashboardPageModel creation and validation."""

    def test_dashboard_page_model_creation(self):
        """Test creating a DashboardPageModel with default values."""
        model = DashboardPageModel()
        self.assertEqual(model.page_type, PageTypeEnum.DASHBOARD)
        self.assertEqual(model.name, "")
        self.assertEqual(model.description, "")
        self.assertEqual(model.is_react_enabled, False)
        self.assertEqual(model.static_paths, [])
        self.assertEqual(model.js_libraries, [])

    def test_dashboard_page_model_with_custom_values(self):
        """Test creating a DashboardPageModel with custom values."""
        model = DashboardPageModel(
            name="My Dashboard",
            description="Test dashboard",
            is_react_enabled=True,
            static_paths=["static/css", "static/js"],
        )
        self.assertEqual(model.name, "My Dashboard")
        self.assertEqual(model.description, "Test dashboard")
        self.assertEqual(model.is_react_enabled, True)
        self.assertEqual(model.static_paths, ["static/css", "static/js"])


class TestPageModelFactory(unittest.TestCase):
    """Test PageModelFactory functionality."""

    def test_create_page_model_from_toml_dashboard(self):
        """Test creating a dashboard page model from TOML data."""
        toml_data = {
            "page": {
                "name": "Test Dashboard",
                "description": "A test dashboard",
                "is_react_enabled": True,
            }
        }
        model = PageModelFactory.create_page_model_from_toml(
            toml_data, PageTypeEnum.DASHBOARD
        )
        self.assertIsInstance(model, DashboardPageModel)
        self.assertEqual(model.name, "Test Dashboard")
        self.assertEqual(model.description, "A test dashboard")
        self.assertEqual(model.is_react_enabled, True)

    def test_create_page_model_from_toml_invalid_type(self):
        """Test that invalid page type raises ValueError."""
        toml_data = {"page": {"name": "Test"}}
        with self.assertRaises(ValueError) as context:
            PageModelFactory.create_page_model_from_toml(toml_data, "invalid_type")
        self.assertIn("Unsupported page type", str(context.exception))

    def test_create_page_model_from_project_invalid_type(self):
        """Test that invalid page type raises ValueError for project loading."""
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            with self.assertRaises(ValueError) as context:
                PageModelFactory.create_page_model_from_project(
                    project_path, "invalid_type"
                )
            self.assertIn("Unsupported page type", str(context.exception))
