"""Tests for the pages executor module."""

import unittest
from pathlib import Path
from unittest.mock import ANY
from unittest.mock import MagicMock
from unittest.mock import patch

from cli.pages.executor import create_local_page
from cli.pages.executor import list_local_pages
from cli.pages.executor import logs_local_dev_server
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
        mock_cwd.return_value = Path("/current")
        mock_sanitize.return_value = "test_page"
        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance

        create_local_page(
            name="test_page",
            verbose=True,
            profile="default",
            type=PageTypeEnum.DASHBOARD,
            formatter=MagicMock(),
        )

        mock_pipeline.assert_called_once()
        args, kwargs = mock_pipeline.call_args
        steps, success_message = args[0], kwargs["success_message"]

        self.assertEqual(
            len(steps), 10
        )  # added GetWorkspaceKeyStep + CreateWorkspaceStep
        self.assertIn("Page 'test_page' created", success_message)

        run_data = mock_pipeline_instance.run.call_args[0][0]
        self.assertEqual(run_data["page_name"], "test_page")
        self.assertEqual(run_data["page_label"], "test_page")
        self.assertEqual(
            run_data["project_path"], Path("/current/test_page")
        )  # plain dir
        self.assertNotIn("symlink_path", run_data)
        self.assertNotIn("workspace_key", run_data)
        self.assertNotIn("workspace_path", run_data)

    @patch("cli.pages.executor.Pipeline")
    @patch("cli.pages.executor.sanitize_function_name")
    def test_create_page_absolute_path(self, mock_sanitize, mock_pipeline):
        mock_sanitize.return_value = "test_page"
        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance

        create_local_page(
            name="test_page",
            verbose=False,
            profile="prod",
            type=PageTypeEnum.DASHBOARD,
            formatter=MagicMock(),
        )

        mock_pipeline_instance.run.assert_called_once()
        run_data = mock_pipeline_instance.run.call_args[0][0]

        # project_path is now CWD / name (plain directory, not workspace)
        self.assertNotIn(".ubidots_cli", str(run_data["project_path"]))
        self.assertNotIn("workspace_key", run_data)
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

        start_local_dev_server(verbose=True, formatter=MagicMock())

        # Verify pipeline was created with correct steps and message
        mock_pipeline.assert_called_once()
        args, kwargs = mock_pipeline.call_args
        steps, success_message = args[0], kwargs["success_message"]

        self.assertEqual(len(steps), 22)  # was 23; removed CleanOrphanedPagesStep
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

        stop_local_dev_server(verbose=False, formatter=MagicMock())

        # Verify pipeline was created with correct steps and message
        mock_pipeline.assert_called_once()
        args, kwargs = mock_pipeline.call_args
        steps, success_message = args[0], kwargs["success_message"]

        self.assertEqual(
            len(steps), 13
        )  # added GetArgoImageNameStep + ValidateArgoImageStep
        self.assertEqual(success_message, "Page stopped successfully.")

        # Verify pipeline.run was called with correct data
        mock_pipeline_instance.run.assert_called_once()
        run_data = mock_pipeline_instance.run.call_args[0][0]

        self.assertEqual(run_data["project_path"], Path("/current"))
        self.assertFalse(run_data["verbose"])
        self.assertEqual(run_data["root"], "stop_local_dev_server")


class TestRestartPage(unittest.TestCase):
    @patch("cli.pages.executor.Pipeline")
    @patch("pathlib.Path.cwd")
    def test_restart_page(self, mock_cwd, mock_pipeline):
        mock_cwd.return_value = Path("/current")
        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance

        from cli.pages.executor import restart_local_dev_server

        restart_local_dev_server(verbose=False, formatter=MagicMock())

        args, kwargs = mock_pipeline.call_args
        steps = args[0]
        self.assertEqual(
            len(steps), 24
        )  # added GetArgoImageNameStep + ValidateArgoImageStep
        self.assertEqual(kwargs["success_message"], "Page restarted successfully.")


class TestStatusPage(unittest.TestCase):
    """Test status_page executor function."""

    @patch("cli.pages.executor.Pipeline")
    @patch("pathlib.Path.cwd")
    def test_status_page(self, mock_cwd, mock_pipeline):
        """Test getting page status."""
        mock_cwd.return_value = Path("/current")
        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance

        show_local_dev_server_status(verbose=False, formatter=MagicMock())

        # Verify pipeline was created with correct steps and message
        mock_pipeline.assert_called_once()
        args, kwargs = mock_pipeline.call_args
        steps, success_message = args[0], kwargs["success_message"]

        self.assertEqual(
            len(steps), 8
        )  # TryGetArgoPortStep replaces GetContainerManagerStep + GetNetworkStep + EnsureArgoRunningStep
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

        list_local_pages(verbose=True, formatter=MagicMock())

        # Verify pipeline was created with correct steps and message
        mock_pipeline.assert_called_once()
        args, kwargs = mock_pipeline.call_args
        steps, success_message = args[0], kwargs["success_message"]

        self.assertEqual(
            len(steps), 8
        )  # added GetArgoImageNameStep + ValidateArgoImageStep
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
            "GetActiveConfigStep",
            "ValidatePagesAvailabilityPerPlanStep",
            "ValidateTemplateStep",
            "CreateProjectFolderStep",
            "ExtractTemplateStep",
            "ValidateExtractedPageStep",
            "SaveManifestStep",
        ]

        for step_class in mock_step_classes:
            setattr(mock_pipelines, step_class, MagicMock())

        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance

        create_local_page("test", False, "default", PageTypeEnum.DASHBOARD, formatter=MagicMock())

        # Verify all expected pipeline steps were instantiated
        for step_class in mock_step_classes:
            getattr(mock_pipelines, step_class).assert_called_once()

    @patch("cli.pages.executor.pipelines")
    @patch("cli.pages.executor.Pipeline")
    def test_start_page_pipeline_steps(self, mock_pipeline, mock_pipelines):
        """Test that start_page uses correct Argo pipeline steps."""
        # Mock all pipeline step classes
        mock_step_classes = [
            "ValidatePageDirectoryStep",
            "ReadPageMetadataStep",
            "ValidatePageStructureStep",
            "GetClientStep",
            "GetContainerManagerStep",
            "GetPageNameStep",
            "GetWorkspaceKeyStep",
            "ValidatePageNotRunningStep",
            "GetNetworkStep",
            "GetArgoImageNameStep",
            "ValidateArgoImageStep",
            "EnsureArgoRunningStep",
            "CreateWorkspaceStep",  # NEW
            "CopyTrackedFilesStep",  # NEW
            "FindHotReloadPortStep",
            "RenderIndexHtmlStep",
            "RegisterPageInArgoStep",
            "StartCopyWatcherStep",  # NEW
            "StartHotReloadSubprocessStep",
            "StoreHotReloadPortStep",
            "PrintPageUrlStep",
        ]

        for step_class in mock_step_classes:
            setattr(mock_pipelines, step_class, MagicMock())

        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance

        start_local_dev_server(False, formatter=MagicMock())

        # Verify all expected pipeline steps were instantiated
        for step_class in mock_step_classes:
            getattr(mock_pipelines, step_class).assert_called_once()

    @patch("cli.pages.executor.pipelines")
    @patch("cli.pages.executor.Pipeline")
    def test_stop_page_pipeline_steps(self, mock_pipeline, mock_pipelines):
        """Test that stop_local_dev_server uses correct Argo pipeline steps."""
        # Mock all pipeline step classes
        mock_step_classes = [
            "ReadPageMetadataStep",
            "GetClientStep",
            "GetContainerManagerStep",
            "GetPageNameStep",
            "GetWorkspaceKeyStep",
            "ValidatePageRunningStep",
            "GetNetworkStep",
            "GetArgoImageNameStep",
            "ValidateArgoImageStep",
            "EnsureArgoRunningStep",
            "DeregisterPageFromArgoStep",
            "StopCopyWatcherStep",  # NEW
            "StopHotReloadSubprocessStep",
        ]

        for step_class in mock_step_classes:
            setattr(mock_pipelines, step_class, MagicMock())

        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance

        stop_local_dev_server(verbose=False, formatter=MagicMock())

        # Verify all expected pipeline steps were instantiated
        for step_class in mock_step_classes:
            getattr(mock_pipelines, step_class).assert_called_once()


class TestLogsPage(unittest.TestCase):
    """Test logs_local_dev_server executor function."""

    @patch("cli.pages.executor.Pipeline")
    def test_logs_page_runs_pipeline(self, mock_pipeline_cls):
        """Test that logs_local_dev_server builds and runs a pipeline."""
        mock_pipeline = MagicMock()
        mock_pipeline_cls.return_value = mock_pipeline
        logs_local_dev_server(tail="all", follow=False, verbose=False, formatter=MagicMock())
        mock_pipeline.run.assert_called_once()
        run_data = mock_pipeline.run.call_args[0][0]
        assert run_data["tail"] == "all"
        assert run_data["follow"] is False

    @patch("cli.pages.executor.Pipeline")
    def test_logs_page_passes_tail_and_follow(self, mock_pipeline_cls):
        """Test that tail and follow are forwarded to the pipeline data."""
        mock_pipeline = MagicMock()
        mock_pipeline_cls.return_value = mock_pipeline
        logs_local_dev_server(tail="50", follow=True, verbose=True, formatter=MagicMock())
        run_data = mock_pipeline.run.call_args[0][0]
        assert run_data["tail"] == "50"
        assert run_data["follow"] is True

    @patch("cli.pages.executor.Pipeline")
    @patch("pathlib.Path.cwd")
    def test_logs_page_pipeline_steps(self, mock_cwd, mock_pipeline):
        mock_cwd.return_value = Path("/current")
        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance

        logs_local_dev_server(tail="all", follow=False, verbose=False, formatter=MagicMock())

        args, _kwargs = mock_pipeline.call_args
        steps = args[0]
        self.assertEqual(len(steps), 5)  # was 4; added GetPageNameStep
