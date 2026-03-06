"""Tests for the pages executor module."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

from cli.pages.executor import create_local_page
from cli.pages.executor import list_local_pages
from cli.pages.executor import restart_local_dev_server
from cli.pages.executor import show_local_dev_server_status
from cli.pages.executor import start_local_dev_server
from cli.pages.executor import stop_local_dev_server
from cli.pages.models import PageTypeEnum


class TestCreatePage(unittest.TestCase):
    """Test create_page executor function."""

    @patch("cli.pages.executor.Pipeline")
    @patch("cli.pages.executor.sanitize_function_name")
    @patch("pathlib.Path.cwd")
    def test_create_page_relative_path(self, mock_cwd, mock_sanitize, mock_pipeline):
        """Test creating page with relative path."""
        mock_cwd.return_value = Path("/current")
        mock_sanitize.return_value = "test_page"
        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance

        create_local_page(
            name="test_page",
            verbose=True,
            profile="default",
            type=PageTypeEnum.DASHBOARD,
        )

        # Verify pipeline was created with correct steps and message
        mock_pipeline.assert_called_once()
        args, kwargs = mock_pipeline.call_args
        steps, success_message = args[0], kwargs["success_message"]

        self.assertEqual(len(steps), 10)  # 10 pipeline steps
        self.assertIn("Page 'test_page' created", success_message)

        # Verify pipeline.run was called with correct data
        mock_pipeline_instance.run.assert_called_once()
        run_data = mock_pipeline_instance.run.call_args[0][0]

        self.assertEqual(run_data["page_name"], "test_page")
        self.assertEqual(run_data["page_label"], "test_page")
        self.assertEqual(run_data["project_path"], Path("/current/test_page"))
        self.assertEqual(run_data["profile"], "default")
        self.assertEqual(run_data["page_type"], PageTypeEnum.DASHBOARD)
        self.assertTrue(run_data["verbose"])
        self.assertTrue(run_data["clean_directory_if_validation_fails"])

    @patch("cli.pages.executor.Pipeline")
    @patch("cli.pages.executor.sanitize_function_name")
    def test_create_page_absolute_path(self, mock_sanitize, mock_pipeline):
        """Test creating page with absolute path."""
        mock_sanitize.return_value = "test_page"
        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance

        create_local_page(
            name="/absolute/test_page",
            verbose=False,
            profile="prod",
            type=PageTypeEnum.DASHBOARD,
        )

        # Verify pipeline.run was called with absolute path
        mock_pipeline_instance.run.assert_called_once()
        run_data = mock_pipeline_instance.run.call_args[0][0]

        self.assertEqual(run_data["project_path"], Path("/absolute/test_page"))
        self.assertFalse(run_data["verbose"])
        self.assertEqual(run_data["profile"], "prod")


class TestStartPage(unittest.TestCase):
    """Test start_page executor function."""

    @patch("cli.pages.executor.Pipeline")
    @patch("pathlib.Path.cwd")
    def test_start_page(self, mock_cwd, mock_pipeline):
        """Test starting page."""
        mock_cwd.return_value = Path("/current")
        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance

        start_local_dev_server(verbose=True)

        # Verify pipeline was created with correct steps and message
        mock_pipeline.assert_called_once()
        args, kwargs = mock_pipeline.call_args
        steps, success_message = args[0], kwargs["success_message"]

        self.assertEqual(len(steps), 10)  # 10 pipeline steps
        self.assertEqual(success_message, "Page started successfully.")

        # Verify pipeline.run was called with correct data
        mock_pipeline_instance.run.assert_called_once()
        run_data = mock_pipeline_instance.run.call_args[0][0]

        self.assertEqual(run_data["project_path"], Path("/current"))
        self.assertTrue(run_data["verbose"])
        self.assertEqual(run_data["root"], "start_local_dev_server")


class TestStopPage(unittest.TestCase):
    """Test stop_page executor function."""

    @patch("cli.pages.executor.Pipeline")
    @patch("pathlib.Path.cwd")
    def test_stop_page(self, mock_cwd, mock_pipeline):
        """Test stopping page."""
        mock_cwd.return_value = Path("/current")
        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance

        stop_local_dev_server(verbose=False)

        # Verify pipeline was created with correct steps and message
        mock_pipeline.assert_called_once()
        args, kwargs = mock_pipeline.call_args
        steps, success_message = args[0], kwargs["success_message"]

        self.assertEqual(len(steps), 7)  # 7 pipeline steps
        self.assertEqual(success_message, "Page stopped successfully.")

        # Verify pipeline.run was called with correct data
        mock_pipeline_instance.run.assert_called_once()
        run_data = mock_pipeline_instance.run.call_args[0][0]

        self.assertEqual(run_data["project_path"], Path("/current"))
        self.assertFalse(run_data["verbose"])
        self.assertEqual(run_data["root"], "stop_local_dev_server")


class TestRestartPage(unittest.TestCase):
    """Test restart_page executor function."""

    @patch("cli.pages.executor.Pipeline")
    @patch("pathlib.Path.cwd")
    def test_restart_page(self, mock_cwd, mock_pipeline):
        """Test restarting page."""
        mock_cwd.return_value = Path("/current")
        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance

        restart_local_dev_server(verbose=True)

        # Verify pipeline was created with correct steps and message
        mock_pipeline.assert_called_once()
        args, kwargs = mock_pipeline.call_args
        steps, success_message = args[0], kwargs["success_message"]

        self.assertEqual(len(steps), 10)  # 10 pipeline steps
        self.assertEqual(success_message, "Page restarted successfully.")

        # Verify pipeline.run was called with correct data
        mock_pipeline_instance.run.assert_called_once()
        run_data = mock_pipeline_instance.run.call_args[0][0]

        self.assertEqual(run_data["project_path"], Path("/current"))
        self.assertTrue(run_data["verbose"])
        self.assertEqual(run_data["root"], "restart_local_dev_server")


class TestStatusPage(unittest.TestCase):
    """Test status_page executor function."""

    @patch("cli.pages.executor.Pipeline")
    @patch("pathlib.Path.cwd")
    def test_status_page(self, mock_cwd, mock_pipeline):
        """Test getting page status."""
        mock_cwd.return_value = Path("/current")
        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance

        show_local_dev_server_status(verbose=False)

        # Verify pipeline was created with correct steps and message
        mock_pipeline.assert_called_once()
        args, kwargs = mock_pipeline.call_args
        steps, success_message = args[0], kwargs["success_message"]

        self.assertEqual(len(steps), 7)  # 7 pipeline steps
        self.assertEqual(success_message, "")  # Empty success message

        # Verify pipeline.run was called with correct data
        mock_pipeline_instance.run.assert_called_once()
        run_data = mock_pipeline_instance.run.call_args[0][0]

        self.assertEqual(run_data["project_path"], Path("/current"))
        self.assertFalse(run_data["verbose"])
        self.assertEqual(run_data["root"], "show_local_dev_server_status")


class TestListPages(unittest.TestCase):
    """Test list_pages executor function."""

    @patch("cli.pages.executor.Pipeline")
    def test_list_pages(self, mock_pipeline):
        """Test listing all pages."""
        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance

        list_local_pages(verbose=True)

        # Verify pipeline was created with correct steps and message
        mock_pipeline.assert_called_once()
        args, kwargs = mock_pipeline.call_args
        steps, success_message = args[0], kwargs["success_message"]

        self.assertEqual(len(steps), 4)  # 4 pipeline steps
        self.assertEqual(success_message, "")  # Empty success message

        # Verify pipeline.run was called with correct data
        mock_pipeline_instance.run.assert_called_once()
        run_data = mock_pipeline_instance.run.call_args[0][0]

        self.assertTrue(run_data["verbose"])
        self.assertEqual(run_data["root"], "list_local_pages")
        # list_pages doesn't need project_path
        self.assertNotIn("project_path", run_data)


class TestExecutorIntegration(unittest.TestCase):
    """Test executor functions integration aspects."""

    @patch("cli.pages.executor.pipelines")
    @patch("cli.pages.executor.Pipeline")
    def test_create_page_pipeline_steps(self, mock_pipeline, mock_pipelines):
        """Test that create_page uses correct pipeline steps."""
        # Mock all pipeline step classes
        mock_step_classes = [
            "ValidateNotRunningFromPageDirectoryStep",
            "ValidateCurrentPageExistsStep",
            "GetActiveConfigStep",
            "ValidatePagesAvailabilityPerPlanStep",
            "ValidateTemplateStep",
            "CreateProjectFolderStep",
            "ExtractTemplateStep",
            "ValidateExtractedPageStep",
            "SaveManifestStep",
            "EnsureDockerImageStep",
        ]

        for step_class in mock_step_classes:
            setattr(mock_pipelines, step_class, MagicMock())

        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance

        create_local_page("test", False, "default", PageTypeEnum.DASHBOARD)

        # Verify all expected pipeline steps were instantiated
        for step_class in mock_step_classes:
            getattr(mock_pipelines, step_class).assert_called_once()

    @patch("cli.pages.executor.pipelines")
    @patch("cli.pages.executor.Pipeline")
    def test_start_page_pipeline_steps(self, mock_pipeline, mock_pipelines):
        """Test that start_page uses correct pipeline steps."""
        # Mock all pipeline step classes
        mock_step_classes = [
            "ValidatePageDirectoryStep",
            "ReadPageMetadataStep",
            "ValidatePageStructureStep",
            "GetClientStep",
            "GetContainerManagerStep",
            "GetPageNameStep",
            "ValidatePageNotRunningStep",
            "EnsureFlaskManagerStep",
            "StartPageContainerStep",
            "PrintPageUrlStep",
        ]

        for step_class in mock_step_classes:
            setattr(mock_pipelines, step_class, MagicMock())

        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance

        start_local_dev_server(False)

        # Verify all expected pipeline steps were instantiated
        for step_class in mock_step_classes:
            getattr(mock_pipelines, step_class).assert_called_once()
