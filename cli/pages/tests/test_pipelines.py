import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock
from unittest.mock import patch

from cli.pages.exceptions import PageAlreadyExistsInCurrentDirectoryError
from cli.pages.exceptions import PageIsAlreadyRunningError
from cli.pages.exceptions import PageIsAlreadyStoppedError
from cli.pages.exceptions import PageWithNameAlreadyExistsError
from cli.pages.models import PageTypeEnum
from cli.pages.pipelines import CreateProjectFolderStep
from cli.pages.pipelines import GetPageStatusStep
from cli.pages.pipelines import ListAllPagesStep
from cli.pages.pipelines import ReadPageMetadataStep
from cli.pages.pipelines import SaveManifestStep
from cli.pages.pipelines import StopPageContainerStep
from cli.pages.pipelines import ValidateCurrentPageExistsStep
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

    @patch("cli.pages.pipelines.dev_scaffold.settings")
    def test_validate_current_page_exists_step_exists(self, mock_settings):
        mock_settings.PAGES.PROJECT_METADATA_FILE = ".manifest.yaml"

        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_page"
            project_path.mkdir()

            data = {"project_path": project_path, "page_name": "test_page"}

            step = ValidateCurrentPageExistsStep()

            with self.assertRaises(PageWithNameAlreadyExistsError):
                step.execute(data)

    @patch("cli.pages.pipelines.dev_scaffold.settings")
    def test_validate_current_page_exists_step_not_exists(self, mock_settings):
        mock_settings.PAGES.PROJECT_METADATA_FILE = ".manifest.yaml"

        with TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_page"

            data = {"project_path": project_path, "page_name": "test_page"}

            step = ValidateCurrentPageExistsStep()
            result = step.execute(data)

            self.assertEqual(result, data)

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


class TestContainerSteps(unittest.TestCase):

    @patch("cli.pages.pipelines.dev_engine.get_page_container")
    @patch("cli.pages.pipelines.dev_engine.is_container_running")
    @patch("cli.pages.pipelines.dev_engine.generate_page_url")
    @patch("cli.pages.pipelines.dev_engine.settings")
    def test_validate_page_not_running_step_not_running(
        self, mock_settings, mock_generate_url, mock_is_running, mock_get_container
    ):
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_is_running.return_value = False

        data = {"container_manager": MagicMock(), "page_name": "test_page"}

        step = ValidatePageNotRunningStep()
        result = step.execute(data)

        self.assertEqual(result, data)

    @patch("cli.pages.pipelines.dev_engine.get_page_container")
    @patch("cli.pages.pipelines.dev_engine.is_container_running")
    @patch("cli.pages.pipelines.dev_engine.generate_page_url")
    @patch("cli.pages.pipelines.dev_engine.settings")
    def test_validate_page_not_running_step_is_running(
        self, mock_settings, mock_generate_url, mock_is_running, mock_get_container
    ):
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_is_running.return_value = True
        mock_generate_url.return_value = "http://localhost:8090/"
        mock_settings.PAGES.ROUTING_MODE = "port"

        data = {"container_manager": MagicMock(), "page_name": "test_page"}

        step = ValidatePageNotRunningStep()

        with self.assertRaises(PageIsAlreadyRunningError):
            step.execute(data)

    @patch("cli.pages.pipelines.dev_engine.get_page_container")
    @patch("cli.pages.pipelines.dev_engine.is_container_running")
    def test_validate_page_running_step_is_running(
        self, mock_is_running, mock_get_container
    ):
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_is_running.return_value = True

        data = {"container_manager": MagicMock(), "page_name": "test_page"}

        step = ValidatePageRunningStep()
        result = step.execute(data)

        self.assertEqual(result, data)

    @patch("cli.pages.pipelines.dev_engine.get_page_container")
    @patch("cli.pages.pipelines.dev_engine.is_container_running")
    def test_validate_page_running_step_not_running(
        self, mock_is_running, mock_get_container
    ):
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_is_running.return_value = False

        data = {"container_manager": MagicMock(), "page_name": "test_page"}

        step = ValidatePageRunningStep()

        with self.assertRaises(PageIsAlreadyStoppedError):
            step.execute(data)

    @patch("cli.pages.pipelines.dev_engine.stop_page_container")
    def test_stop_page_container_step(self, mock_stop_container):
        data = {"container_manager": MagicMock(), "page_name": "test_page"}

        step = StopPageContainerStep()
        result = step.execute(data)

        self.assertEqual(result, data)
        mock_stop_container.assert_called_once_with(
            container_manager=data["container_manager"], page_name="test_page"
        )

    @patch("cli.pages.pipelines.dev_engine.get_page_container")
    @patch("cli.pages.pipelines.dev_engine.is_container_running")
    @patch("cli.pages.pipelines.dev_engine.generate_page_url")
    @patch("cli.pages.pipelines.dev_engine.settings")
    def test_get_page_status_step_running(
        self, mock_settings, mock_generate_url, mock_is_running, mock_get_container
    ):
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        mock_is_running.return_value = True
        mock_generate_url.return_value = "http://localhost:8090/"
        mock_settings.PAGES.ROUTING_MODE = "port"

        data = {"container_manager": MagicMock(), "page_name": "test_page"}

        step = GetPageStatusStep()
        result = step.execute(data)

        expected_data = data.copy()
        expected_data.update(
            {"page_status": "running", "page_url": "http://localhost:8090/"}
        )
        self.assertEqual(result, expected_data)

    @patch("cli.pages.pipelines.dev_engine.get_page_container")
    def test_get_page_status_step_stopped(self, mock_get_container):
        mock_get_container.return_value = None

        data = {"container_manager": MagicMock(), "page_name": "test_page"}

        step = GetPageStatusStep()
        result = step.execute(data)

        expected_data = data.copy()
        expected_data.update({"page_status": "stopped", "page_url": ""})
        self.assertEqual(result, expected_data)

    @patch("cli.pages.pipelines.dev_engine.page_engine_settings")
    @patch("cli.pages.pipelines.dev_engine.generate_page_url")
    @patch("cli.pages.pipelines.dev_engine.settings")
    def test_list_all_pages_step(
        self, mock_settings, mock_generate_url, mock_page_settings
    ):
        mock_page_settings.CONTAINER.PAGE.PREFIX_NAME = "page"
        mock_settings.PAGES.ROUTING_MODE = "port"
        mock_generate_url.return_value = "http://localhost:8090/"

        mock_container1 = MagicMock()
        mock_container1.name = "page-test_page1"
        mock_container1.status = "running"

        mock_container2 = MagicMock()
        mock_container2.name = "page-test_page2"
        mock_container2.status = "exited"

        mock_container_manager = MagicMock()
        mock_container_manager.list.return_value = [mock_container1, mock_container2]

        data = {"container_manager": mock_container_manager}

        step = ListAllPagesStep()
        result = step.execute(data)

        expected_pages_info = [
            {
                "name": "test_page1",
                "status": "running",
                "url": "http://localhost:8090/",
            },
            {"name": "test_page2", "status": "stopped", "url": "-"},
        ]

        expected_data = data.copy()
        expected_data["pages_info"] = expected_pages_info
        self.assertEqual(result, expected_data)
