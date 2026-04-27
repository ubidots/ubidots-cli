import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock
from unittest.mock import patch

from cli.pages.exceptions import PageAlreadyExistsInCurrentDirectoryError
from cli.pages.exceptions import PageIsAlreadyRunningError
from cli.pages.exceptions import PageIsAlreadyStoppedError
from cli.pages.models import PageTypeEnum
from cli.pages.pipelines import CreateProjectFolderStep
from cli.pages.pipelines import GetPageStatusStep
from cli.pages.pipelines import ListAllPagesStep
from cli.pages.pipelines import PrintkeyStep
from cli.pages.pipelines import ReadPageMetadataStep
from cli.pages.pipelines import SaveManifestStep
from cli.pages.pipelines import ValidateNotRunningFromPageDirectoryStep
from cli.pages.pipelines import ValidatePageDirectoryStep
from cli.pages.pipelines import ValidatePageNotRunningStep
from cli.pages.pipelines import ValidatePageRunningStep


class TestValidationSteps(unittest.TestCase):

    @patch("cli.pages.pipelines.dev_scaffold.settings")
    def test_validate_not_running_from_page_directory_step_exists(self, mock_settings):
        mock_settings.PAGES.PROJECT_MANIFEST_FILE = ".manifest.yaml"

        with TemporaryDirectory() as temp_dir:
            manifest_file = Path(temp_dir) / ".manifest.yaml"
            manifest_file.touch()

            step = ValidateNotRunningFromPageDirectoryStep()

            with (
                patch("pathlib.Path.cwd", return_value=Path(temp_dir)),
                self.assertRaises(PageAlreadyExistsInCurrentDirectoryError),
            ):
                step.execute({})

    @patch("cli.pages.pipelines.dev_scaffold.settings")
    def test_validate_not_running_from_page_directory_step_not_exists(
        self, mock_settings
    ):
        mock_settings.PAGES.PROJECT_MANIFEST_FILE = ".manifest.yaml"

        with TemporaryDirectory() as temp_dir:
            step = ValidateNotRunningFromPageDirectoryStep()

            with patch("pathlib.Path.cwd", return_value=Path(temp_dir)):
                result = step.execute({})

            self.assertEqual(result, {})

    def test_validate_page_directory_step_exists(self):
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            manifest_file = project_path / "manifest.toml"
            manifest_file.touch()

            data = {"project_path": project_path}

            step = ValidatePageDirectoryStep()
            result = step.execute(data)

            self.assertEqual(result, data)

    def test_validate_page_directory_step_not_exists(self):
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            data = {"project_path": project_path}

            step = ValidatePageDirectoryStep()

            with self.assertRaises(FileNotFoundError):
                step.execute(data)


class TestCreationSteps(unittest.TestCase):

    def test_create_project_folder_step(self):
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_page"

            data = {"project_path": project_path}

            step = CreateProjectFolderStep()
            result = step.execute(data)

            self.assertEqual(result, data)
            self.assertTrue(project_path.exists())
            self.assertTrue(project_path.is_dir())

    @patch("cli.pages.pipelines.dev_scaffold.create_and_save_page_manifest")
    def test_save_manifest_step(self, mock_create_manifest):
        mock_metadata = MagicMock()
        mock_create_manifest.return_value = mock_metadata

        data = {
            "project_path": Path("/test"),
            "page_name": "test_page",
            "page_type": PageTypeEnum.DASHBOARD,
        }

        step = SaveManifestStep()
        result = step.execute(data)

        expected_data = data.copy()
        expected_data["project_metadata"] = mock_metadata
        self.assertEqual(result, expected_data)

        mock_create_manifest.assert_called_once_with(
            Path("/test"), "test_page", PageTypeEnum.DASHBOARD
        )

    @patch("cli.pages.pipelines.dev_engine.read_page_manifest")
    def test_read_page_metadata_step_success(self, mock_read_manifest):
        mock_metadata = MagicMock()
        mock_read_manifest.return_value = mock_metadata

        data = {"project_path": Path("/test")}

        step = ReadPageMetadataStep()
        result = step.execute(data)

        expected_data = data.copy()
        expected_data["project_metadata"] = mock_metadata
        self.assertEqual(result, expected_data)

    @patch("cli.pages.pipelines.dev_engine.read_page_manifest")
    def test_read_page_metadata_step_not_found(self, mock_read_manifest):
        mock_read_manifest.side_effect = FileNotFoundError("Not found")

        data = {"project_path": Path("/test")}

        step = ReadPageMetadataStep()

        with self.assertRaises(FileNotFoundError):
            step.execute(data)


class TestPidBasedSteps(unittest.TestCase):
    """Tests for new pid-file-based pipeline steps."""

    def test_validate_page_not_running_step_not_running(self):
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            data = {"project_path": project_path, "workspace_key": "test-page-abc123"}
            step = ValidatePageNotRunningStep()
            result = step.execute(data)
            self.assertEqual(result, data)

    def test_validate_page_not_running_step_is_running(self):
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            pid_file = project_path / ".pid"
            pid_file.write_text("12345")

            data = {"project_path": project_path, "workspace_key": "test-page-abc123"}
            step = ValidatePageNotRunningStep()

            with patch("os.kill"), self.assertRaises(
                PageIsAlreadyRunningError
            ):  # Simulate process exists
                step.execute(data)

    def test_validate_page_running_step_is_running(self):
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            pid_file = project_path / ".pid"
            pid_file.write_text("12345")

            data = {"project_path": project_path, "workspace_key": "test-page-abc123"}
            step = ValidatePageRunningStep()

            with patch("os.kill"):  # Simulate process exists
                result = step.execute(data)

            self.assertEqual(result, data)

    def test_validate_page_running_step_not_running(self):
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            data = {"project_path": project_path, "workspace_key": "test-page-abc123"}
            step = ValidatePageRunningStep()

            with self.assertRaises(PageIsAlreadyStoppedError):
                step.execute(data)

    def test_get_page_status_step_stopped_no_pid(self):
        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            data = {
                "project_path": project_path,
                "workspace_key": "test-page",
                "argo_adapter_port": 8040,
            }
            step = GetPageStatusStep()
            with patch("httpx.get", side_effect=Exception("connection refused")):
                result = step.execute(data)
            self.assertEqual(result["page_status"], "stopped")
            self.assertEqual(result["page_url"], "")

    def test_list_all_pages_step_empty_workspace(self):
        with TemporaryDirectory() as temp_dir:
            data = {"argo_adapter_port": 8040}
            step = ListAllPagesStep()
            with (
                patch(
                    "cli.pages.pipelines.dev_engine.get_pages_workspace",
                    return_value=Path(temp_dir),
                ),
                patch("httpx.get", side_effect=Exception("connection refused")),
            ):
                result = step.execute(data)
            self.assertEqual(result["pages_info"], [])

    def test_list_all_pages_step_includes_source_path(self):
        with TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            page_dir = workspace / "my-page-abc12345"
            page_dir.mkdir()
            source_dir = workspace / "source" / "my-page"
            source_dir.mkdir(parents=True)
            (page_dir / ".source_path").write_text(str(source_dir), encoding="utf-8")

            data = {"argo_adapter_port": 8040}
            step = ListAllPagesStep()
            with (
                patch(
                    "cli.pages.pipelines.dev_engine.get_pages_workspace",
                    return_value=workspace,
                ),
                patch("httpx.get", side_effect=Exception("connection refused")),
            ):
                result = step.execute(data)

            self.assertEqual(len(result["pages_info"]), 1)
            self.assertEqual(result["pages_info"][0]["path"], str(source_dir))
            self.assertNotEqual(result["pages_info"][0]["status"], "orphaned")

    def test_list_all_pages_step_path_fallback_when_missing(self):
        with TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            page_dir = workspace / "my-page-abc12345"
            page_dir.mkdir()
            # No .source_path file

            data = {"argo_adapter_port": 8040}
            step = ListAllPagesStep()
            with (
                patch(
                    "cli.pages.pipelines.dev_engine.get_pages_workspace",
                    return_value=workspace,
                ),
                patch("httpx.get", side_effect=Exception("connection refused")),
            ):
                result = step.execute(data)

            self.assertEqual(result["pages_info"][0]["path"], "-")

    def test_list_all_pages_step_orphaned_when_source_dir_deleted(self):
        with TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            page_dir = workspace / "my-page-abc12345"
            page_dir.mkdir()
            # .source_path points to a directory that no longer exists
            (page_dir / ".source_path").write_text(
                "/nonexistent/path/my-page", encoding="utf-8"
            )

            data = {"argo_adapter_port": 8040}
            step = ListAllPagesStep()
            with (
                patch(
                    "cli.pages.pipelines.dev_engine.get_pages_workspace",
                    return_value=workspace,
                ),
                patch("httpx.get", side_effect=Exception("connection refused")),
            ):
                result = step.execute(data)

            entry = result["pages_info"][0]
            self.assertEqual(entry["status"], "orphaned")
            self.assertEqual(entry["url"], "-")


class TestPrintkeyStep(unittest.TestCase):

    def test_prints_existing_key(self):
        step = PrintkeyStep(key="logs")
        data = {"logs": "line1\nline2"}
        with patch("cli.pages.pipelines.dev_engine.typer.echo") as mock_echo:
            result = step.execute(data)
        mock_echo.assert_called_once_with("line1\nline2")
        self.assertEqual(result, data)

    def test_skips_missing_key(self):
        step = PrintkeyStep(key="nonexistent")
        data = {"logs": "something"}
        with patch("cli.pages.pipelines.dev_engine.typer.echo") as mock_echo:
            result = step.execute(data)
        mock_echo.assert_not_called()
        self.assertEqual(result, data)

    def test_skips_empty_key(self):
        step = PrintkeyStep(key="")
        data = {"logs": "something"}
        with patch("cli.pages.pipelines.dev_engine.typer.echo") as mock_echo:
            result = step.execute(data)
        mock_echo.assert_not_called()
        self.assertEqual(result, data)
