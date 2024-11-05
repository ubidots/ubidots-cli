import zipfile
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import ANY
from unittest.mock import MagicMock
from unittest.mock import patch

import httpx
import pytest
import typer

from cli.functions import pipelines
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.enums import FunctionMethodEnum
from cli.functions.enums import FunctionRuntimeLayerTypeEnum
from cli.functions.exceptions import FolderAlreadyExistsError
from cli.functions.exceptions import PermissionDeniedError
from cli.functions.exceptions import TemplateNotFoundError
from cli.functions.models import FunctionProjectMetadata
from cli.settings import settings


class TestValidateTemplateStep:
    @patch("pathlib.Path.exists", return_value=True)
    def test_execute_success(self, mock_exists):
        # Setup
        step = pipelines.ValidateTemplateStep()
        data = {
            "template_file": Path("/path/to/template.zip"),
            "language": FunctionLanguageEnum.PYTHON,
        }
        # Action
        result = step.execute(data)
        # Assert
        assert result == data
        mock_exists.assert_called_once_with()

    @patch("pathlib.Path.exists", return_value=False)
    def test_execute_error(self, mock_exists):
        # Setup
        step = pipelines.ValidateTemplateStep()
        data = {
            "template_file": Path("/path/to/template.zip"),
            "language": FunctionLanguageEnum.PYTHON,
        }
        # Action
        with pytest.raises(TemplateNotFoundError) as exc_info:
            step.execute(data)
        # Assert
        assert f"Template for '{FunctionLanguageEnum.PYTHON}' not found at" in str(
            exc_info.value
        )
        mock_exists.assert_called_once_with()

    def test_execute_with_temporal_file_success(self):
        # Setup
        with NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        step = pipelines.ValidateTemplateStep()
        data = {"template_file": temp_path, "language": FunctionLanguageEnum.PYTHON}
        # Action
        result = step.execute(data)
        # Assert
        assert result == data
        temp_path.unlink()

    def test_execute_with_temporal_missing_file_raises_template_not_found_error(self):
        # Setup
        with NamedTemporaryFile(delete=False) as temp_file:
            temp_path_file = Path(temp_file.name)
        temp_path_file.unlink()
        step = pipelines.ValidateTemplateStep()
        data = {
            "template_file": temp_path_file,
            "language": FunctionLanguageEnum.PYTHON,
        }
        # Action
        with pytest.raises(TemplateNotFoundError) as exc_info:
            step.execute(data)
        # Assert
        assert (
            f"Template for '{FunctionLanguageEnum.PYTHON}' not found at '{temp_path_file}'."
            in str(exc_info.value)
        )

    def test_execute_with_real_file_raises_template_not_found_error(self):
        language = "java"
        real_template_path_file = settings.FUNCTIONS.TEMPLATES_PATH / f"{language}.zip"
        # Setup
        step = pipelines.ValidateTemplateStep()
        data = {"template_file": real_template_path_file, "language": language}
        # Action
        with pytest.raises(TemplateNotFoundError) as exc_info:
            step.execute(data)
        # Assert
        assert (
            f"Template for '{language}' not found at '{real_template_path_file}'."
            in str(exc_info.value)
        )


class TestCreateProjectFolderStep:
    @patch("pathlib.Path.exists", return_value=False)
    @patch("pathlib.Path.mkdir")
    def test_execute_success(self, mock_mkdir, mock_exists):
        # Setup
        step = pipelines.CreateProjectFolderStep()
        data = {"project_path": Path("/path/to/project_folder")}
        # Action
        result = step.execute(data)
        # Assert
        assert result == data
        mock_exists.assert_called_once_with()
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=False)

    @patch("pathlib.Path.exists", return_value=True)
    def test_execute_raises_folder_already_exists_error(self, mock_exists):
        # Setup
        step = pipelines.CreateProjectFolderStep()
        data = {"project_path": Path("/path/to/existing_folder")}
        # Action
        with pytest.raises(FolderAlreadyExistsError) as exc_info:
            step.execute(data)
        # Assert
        assert f"A folder named '{data['project_path'].name}' already exists." in str(
            exc_info.value
        )
        mock_exists.assert_called_once_with()

    @patch("pathlib.Path.exists", return_value=False)
    @patch("pathlib.Path.mkdir", side_effect=PermissionError("Permission denied"))
    def test_execute_raises_permission_denied_error(self, mock_mkdir, mock_exists):
        # Setup
        step = pipelines.CreateProjectFolderStep()
        data = {"project_path": Path("/path/to/protected_folder")}
        # Action
        with pytest.raises(PermissionDeniedError) as exc_info:
            step.execute(data)
        # Assert
        assert "Permission denied: " in str(exc_info.value)
        mock_exists.assert_called_once_with()
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=False)


class TestExtractTemplateStep:
    @patch("zipfile.ZipFile.extractall")
    @patch("zipfile.ZipFile.__init__", return_value=None)
    def test_execute_success(self, mock_zip_init, mock_extractall):
        # Setup
        step = pipelines.ExtractTemplateStep()
        data = {
            "template_file": Path("/path/to/template.zip"),
            "project_path": Path("/path/to/project_folder"),
        }
        # Action
        result = step.execute(data)
        # Assert
        assert result == data
        mock_zip_init.assert_called_once_with(data["template_file"], "r")
        mock_extractall.assert_called_once_with(data["project_path"])

    @patch("zipfile.ZipFile.__init__", side_effect=FileNotFoundError("File not found"))
    def test_execute_raises_file_not_found_error(self, mock_zip_init):
        # Setup
        step = pipelines.ExtractTemplateStep()
        data = {
            "template_file": Path("/path/to/nonexistent.zip"),
            "project_path": Path("/path/to/project_folder"),
        }
        # Action
        with pytest.raises(FileNotFoundError) as exc_info:
            step.execute(data)
        # Assert
        assert "File not found" in str(exc_info.value)
        mock_zip_init.assert_called_once_with(data["template_file"], "r")

    @patch("zipfile.ZipFile.__init__", side_effect=zipfile.BadZipFile("Bad zip file"))
    def test_execute_raises_bad_zip_file_error(self, mock_zip_init):
        # Setup
        step = pipelines.ExtractTemplateStep()
        data = {
            "template_file": Path("/path/to/corrupt.zip"),
            "project_path": Path("/path/to/project_folder"),
        }
        # Action
        with pytest.raises(zipfile.BadZipFile) as exc_info:
            step.execute(data)
        # Assert
        assert "Bad zip file" in str(exc_info.value)
        mock_zip_init.assert_called_once_with(data["template_file"], "r")


class TestSaveManifestStep:
    @patch("cli.functions.pipelines.save_manifest_project_file")
    def test_execute_with_all_data_provided(self, mock_save_manifest):
        # Setup
        step = pipelines.SaveManifestStep()
        data = {
            "project_path": Path("/path/to/project"),
            "language": FunctionLanguageEnum.PYTHON,
            "runtime": FunctionRuntimeLayerTypeEnum.PYTHON_3_9_BASE,
            "local_label": "local_label_test",
            "function_id": "function_id_test",
            "function_label": "function_label_test",
            "is_raw": True,
            "has_cors": True,
            "cron": "",
            "payload": {"key": "value"},
            "methods": [FunctionMethodEnum.GET, FunctionMethodEnum.POST],
            "timeout": 30,
        }
        # Action
        result = step.execute(data)
        # Assert
        assert result == data
        mock_save_manifest.assert_called_once_with(
            project_path=data["project_path"],
            language=data["language"],
            runtime=data["runtime"],
            local_label=data["local_label"],
            function_id=data["function_id"],
            is_raw=True,
            has_cors=True,
            methods=data["methods"],
            timeout=data["timeout"],
        )

    @patch("cli.functions.pipelines.save_manifest_project_file")
    def test_execute_with_project_metadata_only(self, mock_save_manifest):
        # Setup
        project_metadata = MagicMock()
        project_metadata.project.language = FunctionLanguageEnum.NODEJS
        project_metadata.project.runtime = FunctionRuntimeLayerTypeEnum.NODEJS_20_BASE
        project_metadata.project.local_label = "metadata_label"
        project_metadata.function.id = "metadata_function_id"
        project_metadata.function.label = "metadata_function_label"
        project_metadata.function.is_raw = False
        project_metadata.function.has_cors = False
        project_metadata.function.cron = ""
        project_metadata.function.payload = {"meta_key": "meta_value"}
        project_metadata.function.methods = [FunctionMethodEnum.POST]
        project_metadata.function.timeout = 60
        step = pipelines.SaveManifestStep()
        data = {
            "project_path": Path("/path/to/project"),
            "project_metadata": project_metadata,
        }
        # Action
        result = step.execute(data)
        # Assert
        assert result == data
        mock_save_manifest.assert_called_once_with(
            project_path=data["project_path"],
            language=FunctionLanguageEnum.NODEJS,
            runtime=FunctionRuntimeLayerTypeEnum.NODEJS_20_BASE,
            local_label="metadata_label",
            function_id="metadata_function_id",
            label="metadata_function_label",
            is_raw=False,
            has_cors=False,
            cron="",
            payload={"meta_key": "meta_value"},
            methods=[FunctionMethodEnum.POST],
            timeout=60,
        )

    @patch("cli.functions.pipelines.save_manifest_project_file")
    def test_execute_with_mixed_data_and_metadata(self, mock_save_manifest):
        # Setup
        project_metadata = MagicMock()
        project_metadata.project.language = FunctionLanguageEnum.NODEJS
        project_metadata.project.runtime = FunctionRuntimeLayerTypeEnum.NODEJS_20_LITE
        project_metadata.project.local_label = "metadata_label"
        project_metadata.function.id = "metadata_function_id"
        project_metadata.function.label = "metadata_function_label"
        project_metadata.function.is_raw = False
        project_metadata.function.has_cors = False
        project_metadata.function.cron = ""
        project_metadata.function.payload = "{}"
        project_metadata.function.methods = [FunctionMethodEnum.POST]
        project_metadata.function.timeout = 60
        step = pipelines.SaveManifestStep()
        data = {
            "project_path": Path("/path/to/project"),
            "project_metadata": project_metadata,
            "has_cors": True,
            "is_raw": True,
            "methods": [FunctionMethodEnum.POST, FunctionMethodEnum.GET],
            "timeout": 30,
        }
        # Action
        result = step.execute(data)
        # Assert
        assert result == data
        mock_save_manifest.assert_called_once_with(
            project_path=data["project_path"],
            language=FunctionLanguageEnum.NODEJS,
            runtime=FunctionRuntimeLayerTypeEnum.NODEJS_20_LITE,
            local_label="metadata_label",
            function_id="metadata_function_id",
            label="metadata_function_label",
            is_raw=True,
            has_cors=True,
            payload="{}",
            cron="",
            methods=[FunctionMethodEnum.POST, FunctionMethodEnum.GET],
            timeout=30,
        )


class TestReadManifestStep:
    @patch("cli.functions.pipelines.read_manifest_project_file")
    def test_execute_success(self, mock_read_manifest):
        # Setup
        step = pipelines.ReadManifestStep()
        project_metadata_mock = MagicMock(spec=FunctionProjectMetadata)
        mock_read_manifest.return_value = project_metadata_mock
        data = {"project_path": Path("/path/to/project")}
        # Action
        result = step.execute(data)
        # Assert
        assert result["project_metadata"] == project_metadata_mock
        mock_read_manifest.assert_called_once_with(data["project_path"])

    @patch("cli.functions.pipelines.read_manifest_project_file")
    def test_execute_file_not_found_error(self, mock_read_manifest):
        # Setup
        step = pipelines.ReadManifestStep()
        data = {"project_path": Path("/path/to/nonexistent_project")}
        mock_read_manifest.side_effect = FileNotFoundError(
            "'.metadata.yaml' not found. Are you in the correct project directory?"
        )
        with pytest.raises(FileNotFoundError) as exc_info:
            step.execute(data)
        # Assert
        assert (
            "'.metadata.yaml' not found. Are you in the correct project directory?"
            in str(exc_info.value)
        )
        mock_read_manifest.assert_called_once_with(data["project_path"])

    @patch("cli.functions.pipelines.read_manifest_project_file")
    def test_execute_empty_file_error(self, mock_read_manifest):
        # Setup
        step = pipelines.ReadManifestStep()
        data = {"project_path": Path("/path/to/project_with_empty_manifest")}
        mock_read_manifest.side_effect = ValueError(
            "The '.metadata.yaml' is empty, make sure it has the correct structure."
        )
        # Action
        with pytest.raises(ValueError) as exc_info:
            step.execute(data)
        # Assert
        assert (
            "The '.metadata.yaml' is empty, make sure it has the correct structure."
            in str(exc_info.value)
        )
        mock_read_manifest.assert_called_once_with(data["project_path"])

    @patch("cli.functions.pipelines.read_manifest_project_file")
    def test_execute_invalid_data_error(self, mock_read_manifest):
        # Setup
        step = pipelines.ReadManifestStep()
        data = {"project_path": Path("/path/to/project_with_invalid_manifest")}
        mock_read_manifest.side_effect = ValueError(
            "Invalid input in '.metadata.yaml' file for 'field' -> Invalid data | "
        )
        # Action
        with pytest.raises(ValueError) as exc_info:
            step.execute(data)
        # Assert
        assert "Invalid input in '.metadata.yaml' file" in str(exc_info.value)
        mock_read_manifest.assert_called_once_with(data["project_path"])


class TestGetProjectFilesStep:
    @patch("cli.functions.pipelines.enumerate_project_files")
    def test_execute_success_with_files(self, mock_enumerate_files):
        # Setup
        step = pipelines.GetProjectFilesStep()
        mock_files = [
            Path("/path/to/project/file1.txt"),
            Path("/path/to/project/subdir/file2.txt"),
        ]
        mock_enumerate_files.return_value = mock_files
        data = {"project_path": Path("/path/to/project")}
        # Action
        result = step.execute(data)
        # Assert
        assert result["project_files"] == mock_files
        mock_enumerate_files.assert_called_once_with(data["project_path"])

    @patch("cli.functions.pipelines.enumerate_project_files")
    def test_execute_success_with_no_files(self, mock_enumerate_files):
        # Setup
        step = pipelines.GetProjectFilesStep()
        mock_enumerate_files.return_value = []
        data = {"project_path": Path("/path/to/empty_project")}
        # Action
        result = step.execute(data)
        # Assert
        assert result["project_files"] == []
        mock_enumerate_files.assert_called_once_with(data["project_path"])

    @patch(
        "cli.functions.pipelines.enumerate_project_files",
        side_effect=FileNotFoundError("Directory not found"),
    )
    def test_execute_directory_not_found_error(self, mock_enumerate_files):
        # Setup
        step = pipelines.GetProjectFilesStep()
        data = {"project_path": Path("/path/to/nonexistent_project")}
        # Action
        with pytest.raises(FileNotFoundError) as exc_info:
            step.execute(data)
        # Assert
        assert "Directory not found" in str(exc_info.value)
        mock_enumerate_files.assert_called_once_with(data["project_path"])


class TestValidateProjectStep:
    def test_execute_success_with_all_validations(self):
        # Setup
        step = pipelines.ValidateProjectStep()
        project_metadata_mock = MagicMock()
        project_metadata_mock.project.language.main_file = "main.py"
        project_metadata_mock.function.id = "function_id_test"
        data = {
            "project_path": Path("/path/to/project"),
            "project_files": [Path("/path/to/project/main.py")],
            "project_metadata": project_metadata_mock,
            "validations": {"manifest_file": True, "function_exists": True},
            "root": "some_function",
        }
        # Action
        result = step.execute(data)
        # Assert
        assert result == data

    def test_execute_raises_function_not_registered_error(self):
        # Setup
        step = pipelines.ValidateProjectStep()
        project_metadata_mock = MagicMock()
        project_metadata_mock.function.id = None
        data = {
            "project_path": Path("/path/to/project"),
            "project_files": [Path("/path/to/project/main.py")],
            "project_metadata": project_metadata_mock,
            "validations": {"function_exists": True},
            "root": "some_function",
        }
        # Action
        with pytest.raises(ValueError) as exc_info:
            step.execute(data)
        # Assert
        assert (
            "Function not yet registered or synchronized with the platform. Missing function key."
            in str(exc_info.value)
        )

    def test_execute_raises_main_file_not_found_error(self):
        # Setup
        step = pipelines.ValidateProjectStep()
        project_metadata_mock = MagicMock()
        project_metadata_mock.project.language.main_file = "main.py"
        data = {
            "project_path": Path("/path/to/project"),
            "project_files": [Path("/path/to/project/other_file.py")],
            "project_metadata": project_metadata_mock,
            "validations": {"manifest_file": True},
            "root": "some_function",
        }
        # Action
        with pytest.raises(FileNotFoundError) as exc_info:
            step.execute(data)
        # Assert
        assert (
            str(exc_info.value)
            == "Main file 'main.py' not found in the project directory."
        )

    def test_execute_function_not_registered_with_push_function(self):
        # Setup
        step = pipelines.ValidateProjectStep()
        project_metadata_mock = MagicMock()
        project_metadata_mock.function.id = None
        data = {
            "project_path": Path("/path/to/project"),
            "project_files": [Path("/path/to/project/main.py")],
            "project_metadata": project_metadata_mock,
            "validations": {"function_exists": True},
            "root": "push_function",
            "overwrite": {"confirm": False},
        }
        # Action
        result = step.execute(data)
        # Assert
        assert result["overwrite"]["confirm"] is True


class TestShowStartupInfoStep:
    def test_execute_with_all_data_provided(self, capfd):
        # Setup
        step = pipelines.ShowStartupInfoStep()
        project_metadata_mock = MagicMock()
        project_metadata_mock.project.name = "Test Project"
        project_metadata_mock.project.runtime = (
            FunctionRuntimeLayerTypeEnum.PYTHON_3_11_BASE
        )
        project_metadata_mock.project.local_label = "test_label"
        project_metadata_mock.function.is_raw = False
        project_metadata_mock.function.methods = [
            FunctionMethodEnum.GET,
            FunctionMethodEnum.POST,
        ]
        project_metadata_mock.function.token = "test_token"
        data = {
            "project_metadata": project_metadata_mock,
            "is_raw": True,
            "methods": [FunctionMethodEnum.GET],
            "token": "provided_token",
        }
        # Action
        step.execute(data)
        # Assert
        captured = capfd.readouterr()
        assert "Name: Test Project" in captured.out
        assert (
            f"Runtime: {FunctionRuntimeLayerTypeEnum.PYTHON_3_11_BASE}" in captured.out
        )
        assert "Local label: test_label" in captured.out
        assert "Raw: True" in captured.out
        assert f"Methods: {FunctionMethodEnum.GET}" in captured.out
        assert "Token: provided_token" in captured.out

    def test_execute_without_data(self, capfd):
        # Setup
        step = pipelines.ShowStartupInfoStep()
        project_metadata_mock = MagicMock()
        project_metadata_mock.project.name = "Partial Project"
        project_metadata_mock.project.runtime = (
            FunctionRuntimeLayerTypeEnum.PYTHON_3_11_BASE
        )
        project_metadata_mock.project.local_label = "partial_label"
        project_metadata_mock.function.is_raw = None
        project_metadata_mock.function.methods = [FunctionMethodEnum.POST]
        project_metadata_mock.function.token = "default_token"
        data = {
            "project_metadata": project_metadata_mock,
        }
        # Action
        step.execute(data)
        # Assert
        captured = capfd.readouterr()
        assert "Name: Partial Project" in captured.out
        assert (
            f"Runtime: {FunctionRuntimeLayerTypeEnum.PYTHON_3_11_BASE}" in captured.out
        )
        assert "Local label: partial_label" in captured.out
        assert "Raw: False" in captured.out
        assert f"Methods: {FunctionMethodEnum.POST}" in captured.out
        assert "Token: default_token" in captured.out


class TestConfirmOverwriteStep:
    @patch("typer.confirm", return_value=True)
    def test_execute_with_confirmation(self, mock_confirm):
        # Setup
        step = pipelines.ConfirmOverwriteStep()
        data = {"overwrite": {"confirm": False, "message": "Do you want to overwrite?"}}
        # Action
        result = step.execute(data)
        # Assert
        assert result == data
        mock_confirm.assert_called_once_with("Do you want to overwrite?")

    @patch("typer.confirm", return_value=False)
    def test_execute_without_confirmation_raises_abort(self, mock_confirm):
        # Setup
        step = pipelines.ConfirmOverwriteStep()
        data = {"overwrite": {"confirm": False, "message": "Do you want to overwrite?"}}
        # Action & Assert
        with pytest.raises(typer.Abort) as exc_info:
            step.execute(data)
        # Assert
        assert (
            "Operation cancelled: The overwrite process was aborted by the user."
            in str(exc_info.value)
        )
        mock_confirm.assert_called_once_with("Do you want to overwrite?")

    def test_execute_with_preconfirmed_data(self):
        # Setup
        step = pipelines.ConfirmOverwriteStep()
        data = {"overwrite": {"confirm": True, "message": "Do you want to overwrite?"}}
        # Action
        result = step.execute(data)
        # Assert
        assert result == data


class TestCompressProjectStep:
    @patch("cli.functions.pipelines.compress_project_to_zip")
    def test_execute_success(self, mock_compress):
        # Setup
        mock_zip_file = MagicMock()
        mock_compress.return_value = mock_zip_file
        step = pipelines.CompressProjectStep()
        data = {"project_path": Path("/path/to/project")}
        # Action
        result = step.execute(data)
        # Assert
        assert result["zip_file"] == mock_zip_file
        mock_compress.assert_called_once_with(
            project_path=data["project_path"], exclude_files=step.exclude_files
        )

    @patch("cli.functions.pipelines.compress_project_to_zip")
    def test_execute_with_exclude_files(self, mock_compress):
        # Setup
        step = pipelines.CompressProjectStep()
        data = {"project_path": Path("/path/to/project")}
        expected_exclude_files = [
            settings.FUNCTIONS.PROJECT_METADATA_FILE,
            f".{settings.FUNCTIONS.DEFAULT_MAIN_FUNCTION_NAME}.py",
            f".{settings.FUNCTIONS.DEFAULT_MAIN_FUNCTION_NAME}.js",
            f"{settings.FUNCTIONS.DEFAULT_HANDLER_FILE_NAME}.py",
            f"{settings.FUNCTIONS.DEFAULT_HANDLER_FILE_NAME}.mjs",
            "node_modules",
        ]
        # Action
        step.execute(data)
        # Assert
        mock_compress.assert_called_once_with(
            project_path=data["project_path"], exclude_files=expected_exclude_files
        )
        assert step.exclude_files == expected_exclude_files


class TestExtractProjectStep:
    @patch("zipfile.ZipFile.extractall")
    @patch("zipfile.ZipFile.__init__", return_value=None)
    def test_execute_success(self, mock_zip_init, mock_extractall):
        # Setup
        step = pipelines.ExtractProjectStep()
        mock_response = MagicMock()
        mock_response.content = b"Fake zip content"
        data = {
            "project_path": Path("/path/to/project"),
            "response": mock_response,
        }
        # Action
        result = step.execute(data)
        # Assert
        assert result == data
        mock_zip_init.assert_called_once_with(ANY, "r")
        mock_extractall.assert_called_once_with(data["project_path"])

    @patch("zipfile.ZipFile.__init__", side_effect=zipfile.BadZipFile("Bad zip file"))
    def test_execute_raises_bad_zip_file_error(self, mock_zip_init):
        # Setup
        step = pipelines.ExtractProjectStep()
        mock_response = MagicMock()
        mock_response.content = b"Corrupt zip content"
        data = {
            "project_path": Path("/path/to/project"),
            "response": mock_response,
        }
        # Action
        with pytest.raises(zipfile.BadZipFile) as exc_info:
            step.execute(data)
        # Assert
        assert "Bad zip file" in str(exc_info.value)
        mock_zip_init.assert_called_once_with(ANY, "r")

    @patch("zipfile.ZipFile.__init__", side_effect=FileNotFoundError("File not found"))
    def test_execute_raises_file_not_found_error(self, mock_zip_init):
        # Setup
        step = pipelines.ExtractProjectStep()
        mock_response = MagicMock()
        mock_response.content = b"Valid zip content"
        data = {
            "project_path": Path("/path/to/nonexistent_project"),
            "response": mock_response,
        }
        # Action
        with pytest.raises(FileNotFoundError) as exc_info:
            step.execute(data)
        # Assert
        assert "File not found" in str(exc_info.value)
        mock_zip_init.assert_called_once_with(ANY, "r")


class TestBuildEndpointStep:
    @patch("cli.functions.pipelines.build_endpoint")
    def test_execute_success(self, mock_build_endpoint):
        # Setup
        step = pipelines.BuildEndpointStep(api_route="/api/function")
        project_metadata_mock = MagicMock()
        project_metadata_mock.function.id = "test_function_id"
        mock_url = "https://api.example.com/api/function/test_function_id"
        mock_headers = {"X-Auth-Token": "test_token"}
        mock_build_endpoint.return_value = (mock_url, mock_headers)
        data = {"project_metadata": project_metadata_mock}
        # Action
        result = step.execute(data)
        # Assert
        assert result["url"] == mock_url
        assert result["headers"] == mock_headers
        mock_build_endpoint.assert_called_once_with(
            route=step.api_route, function_key=project_metadata_mock.function.id
        )

    @patch(
        "cli.functions.pipelines.build_endpoint",
        side_effect=Exception("Endpoint build failed"),
    )
    def test_execute_raises_exception(self, mock_build_endpoint):
        # Setup
        step = pipelines.BuildEndpointStep(api_route="/api/function")
        project_metadata_mock = MagicMock()
        project_metadata_mock.function.id = "test_function_id"
        data = {"project_metadata": project_metadata_mock}
        # Action
        with pytest.raises(Exception) as exc_info:
            step.execute(data)
        # Assert
        assert "Endpoint build failed" in str(exc_info.value)
        mock_build_endpoint.assert_called_once_with(
            route=step.api_route, function_key=project_metadata_mock.function.id
        )


class TestCreateFunctionStep:
    @patch("cli.functions.pipelines.build_functions_payload")
    @patch("httpx.Client.post")
    @patch("typer.confirm", return_value=True)
    def test_execute_create_function_success(
        self, mock_confirm, mock_post, mock_build_payload
    ):
        # Setup
        step = pipelines.CreateFunctionStep()
        mock_response = MagicMock()
        mock_response.status_code = httpx.codes.CREATED
        mock_response.json.return_value = {
            "id": "new_function_id",
            "label": "new_function_label",
        }
        mock_post.return_value = mock_response
        mock_build_payload.return_value = {"mocked_payload": True}
        project_metadata_mock = MagicMock()
        project_metadata_mock.function.id = None
        project_metadata_mock.function.label = "Test Function"
        project_metadata_mock.project.name = "Test Project"
        project_metadata_mock.function.methods = [FunctionMethodEnum.POST]
        project_metadata_mock.function.has_cors = False
        project_metadata_mock.function.cron = ""
        project_metadata_mock.project.runtime = (
            FunctionRuntimeLayerTypeEnum.PYTHON_3_11_LITE
        )
        project_metadata_mock.function.is_raw = False
        project_metadata_mock.function.timeout = 30
        project_metadata_mock.function.payload = {}
        data = {
            "url": "https://api.example.com/functions",
            "headers": {"X-Auth-Token": "test_token"},
            "project_metadata": project_metadata_mock,
        }
        # Action
        result = step.execute(data)
        # Assert
        assert result["response"] == mock_response
        assert result["function_id"] == "new_function_id"
        assert result["function_label"] == "new_function_label"
        mock_confirm.assert_called_once_with(
            "This function is not created. Would you like to create a new function and push it?"
        )
        mock_post.assert_called_once_with(
            "https://api.example.com/functions",
            headers=data["headers"],
            json={"mocked_payload": True},
        )

    @patch("typer.confirm", return_value=False)
    def test_execute_user_aborts_creation(self, mock_confirm):
        # Setup
        step = pipelines.CreateFunctionStep()
        project_metadata_mock = MagicMock()
        project_metadata_mock.function.id = None
        data = {
            "url": "https://api.example.com/functions",
            "headers": {"X-Auth-Token": "test_token"},
            "project_metadata": project_metadata_mock,
        }
        # Action
        with pytest.raises(typer.Abort) as exc_info:
            step.execute(data)
        # Assert
        assert (
            "Operation cancelled: The overwrite process was aborted by the user."
            in str(exc_info.value)
        )
        mock_confirm.assert_called_once()

    @patch("httpx.Client.post")
    def test_execute_function_exists_needs_update(self, mock_post):
        # Setup
        step = pipelines.CreateFunctionStep()
        project_metadata_mock = MagicMock()
        project_metadata_mock.function.id = "existing_function_id"
        data = {
            "url": "https://api.example.com/functions",
            "headers": {"X-Auth-Token": "test_token"},
            "project_metadata": project_metadata_mock,
        }
        # Action
        result = step.execute(data)
        # Assert
        assert result["needs_update"] is True
        assert "response" not in result
        mock_post.assert_not_called()


class TestUpdateFunctionStep:
    @patch("httpx.patch")
    @patch("cli.functions.pipelines.build_functions_payload")
    def test_execute_update_function_success(self, mock_build_payload, mock_patch):
        # Setup
        step = pipelines.UpdateFunctionStep()
        mock_response = MagicMock()
        mock_response.status_code = httpx.codes.OK
        mock_patch.return_value = mock_response
        mock_build_payload.return_value = {"mocked_payload": True}
        project_metadata_mock = MagicMock()
        project_metadata_mock.function.id = "existing_function_id"
        project_metadata_mock.function.methods = [FunctionMethodEnum.GET]
        data = {
            "url": "https://api.example.com/functions/existing_function_id",
            "headers": {"X-Auth-Token": "test_token"},
            "project_metadata": project_metadata_mock,
            "needs_update": True,
        }
        # Action
        result = step.execute(data)
        # Assert
        assert result["response"] == mock_response
        mock_patch.assert_called_once_with(
            data["url"], headers=data["headers"], json={"mocked_payload": True}
        )
        mock_build_payload.assert_called_once_with(
            label=project_metadata_mock.function.label or "",
            name=project_metadata_mock.project.name,
            triggers={
                "httpMethods": project_metadata_mock.function.methods,
                "httpHasCors": project_metadata_mock.function.has_cors,
                "schedulerCron": project_metadata_mock.function.cron or None,
            },
            serverless={
                "runtime": project_metadata_mock.project.runtime,
                "isRawFunction": project_metadata_mock.function.is_raw,
                "authToken": None,
                "timeout": project_metadata_mock.function.timeout,
                "params": project_metadata_mock.function.payload,
            },
        )

    @patch("httpx.patch")
    def test_execute_function_does_not_need_update(self, mock_patch):
        # Setup
        step = pipelines.UpdateFunctionStep()
        project_metadata_mock = MagicMock()
        project_metadata_mock.function.id = None
        data = {
            "url": "https://api.example.com/functions/new_function_id",
            "headers": {"X-Auth-Token": "test_token"},
            "project_metadata": project_metadata_mock,
            "needs_update": False,
        }
        # Action
        result = step.execute(data)
        # Assert
        assert result == data
        mock_patch.assert_not_called()

    @patch(
        "httpx.patch",
        side_effect=httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=MagicMock(status_code=401)
        ),
    )
    def test_execute_update_function_http_error(self, mock_patch):
        # Setup
        step = pipelines.UpdateFunctionStep()
        project_metadata_mock = MagicMock()
        project_metadata_mock.function.id = "existing_function_id"
        data = {
            "url": "https://api.example.com/functions/existing_function_id",
            "headers": {"X-Auth-Token": "test_token"},
            "project_metadata": project_metadata_mock,
            "needs_update": True,
        }
        # Action
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            step.execute(data)
        # Assert
        assert "Unauthorized" in str(exc_info.value)
        mock_patch.assert_called_once_with(
            data["url"], headers=data["headers"], json=ANY
        )


class TestUploadFileStep:
    @patch("httpx.Client.post")
    def test_execute_upload_file_success(self, mock_post):
        # Setup
        step = pipelines.UploadFileStep()
        mock_response = MagicMock()
        mock_response.status_code = httpx.codes.OK
        mock_post.return_value = mock_response
        zip_file = BytesIO(b"Fake zip content")
        project_metadata_mock = MagicMock()
        project_metadata_mock.project.name = "TestProject"
        data = {
            "url": "https://api.example.com/upload",
            "headers": {"X-Auth-Token": "test_token"},
            "zip_file": zip_file,
            "project_metadata": project_metadata_mock,
        }
        # Action
        result = step.execute(data)
        # Assert
        assert result["response"] == mock_response
        mock_post.assert_called_once_with(
            url=data["url"],
            headers=data["headers"],
            files={"zipFile": ("TestProject.zip", zip_file, "application/zip")},
        )

    @patch(
        "httpx.Client.post",
        side_effect=httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=MagicMock(status_code=401)
        ),
    )
    def test_execute_upload_file_http_error(self, mock_post):
        # Setup
        step = pipelines.UploadFileStep()
        zip_file = BytesIO(b"Fake zip content")
        project_metadata_mock = MagicMock()
        project_metadata_mock.project.name = "TestProject"
        data = {
            "url": "https://api.example.com/upload",
            "headers": {"X-Auth-Token": "test_token"},
            "zip_file": zip_file,
            "project_metadata": project_metadata_mock,
        }
        # Action
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            step.execute(data)
        # Assert
        assert "Unauthorized" in str(exc_info.value)
        mock_post.assert_called_once_with(
            url=data["url"],
            headers=data["headers"],
            files={"zipFile": ("TestProject.zip", zip_file, "application/zip")},
        )


class TestHttpGetRequestStep:
    @patch("httpx.get")
    def test_execute_get_request_success(self, mock_get):
        # Setup
        step = pipelines.HttpGetRequestStep()
        mock_response = MagicMock()
        mock_response.status_code = httpx.codes.OK
        mock_response.json.return_value = {"results": [{"id": 1, "name": "Test"}]}
        mock_get.return_value = mock_response
        data = {
            "url": "https://api.example.com/data",
            "headers": {"X-Auth-Token": "test_token"},
        }
        # Action
        result = step.execute(data)
        # Assert
        assert result["response"] == mock_response
        assert result["results"] == [{"id": 1, "name": "Test"}]
        mock_get.assert_called_once_with(data["url"], headers=data["headers"])

    @patch(
        "httpx.get",
        side_effect=httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=MagicMock(status_code=404)
        ),
    )
    def test_execute_get_request_http_error(self, mock_get):
        # Setup
        step = pipelines.HttpGetRequestStep()
        data = {
            "url": "https://api.example.com/data",
            "headers": {"X-Auth-Token": "test_token"},
        }
        # Action
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            step.execute(data)
        # Assert
        assert "Not Found" in str(exc_info.value)
        mock_get.assert_called_once_with(data["url"], headers=data["headers"])

    @patch("httpx.get")
    def test_execute_get_request_invalid_json_response(self, mock_get):
        # Setup
        step = pipelines.HttpGetRequestStep()
        mock_response = MagicMock()
        mock_response.status_code = httpx.codes.OK
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response
        data = {
            "url": "https://api.example.com/data",
            "headers": {"X-Auth-Token": "test_token"},
        }
        # Action
        with pytest.raises(ValueError) as exc_info:
            step.execute(data)
        # Assert
        assert "Invalid JSON" in str(exc_info.value)
        mock_get.assert_called_once_with(data["url"], headers=data["headers"])


class TestDownloadFileStep:
    @patch("httpx.get")
    def test_execute_download_file_success(self, mock_get):
        # Setup
        step = pipelines.DownloadFileStep()
        mock_response = MagicMock()
        mock_response.status_code = httpx.codes.OK
        mock_response.content = b"File content"
        mock_get.return_value = mock_response
        data = {
            "url": "https://api.example.com/file",
            "headers": {"Authorization": "Bearer test_token"},
        }
        # Action
        result = step.execute(data)
        # Assert
        assert result["response"] == mock_response
        assert result["response"].content == b"File content"
        mock_get.assert_called_once_with(data["url"], headers=data["headers"])

    @patch(
        "httpx.get",
        side_effect=httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=MagicMock(status_code=404)
        ),
    )
    def test_execute_download_file_http_error(self, mock_get):
        # Setup
        step = pipelines.DownloadFileStep()
        data = {
            "url": "https://api.example.com/file",
            "headers": {"Authorization": "Bearer test_token"},
        }
        # Action
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            step.execute(data)
        # Assert
        assert "Not Found" in str(exc_info.value)
        mock_get.assert_called_once_with(data["url"], headers=data["headers"])


class TestCheckResponseStep:
    @patch("cli.functions.pipelines.check_response_status")
    def test_execute_check_response_success(self, mock_check_response):
        # Setup
        step = pipelines.CheckResponseStep()
        mock_response = MagicMock()
        mock_response.status_code = httpx.codes.OK
        data = {"response": mock_response}
        # Action
        result = step.execute(data)
        # Assert
        assert result == data
        mock_check_response.assert_called_once_with(mock_response)

    @patch(
        "cli.functions.pipelines.check_response_status",
        side_effect=httpx.RequestError("Error occurred"),
    )
    def test_execute_check_response_raises_error(self, mock_check_response):
        # Setup
        step = pipelines.CheckResponseStep()
        mock_response = MagicMock()
        mock_response.status_code = httpx.codes.BAD_REQUEST
        data = {"response": mock_response}
        # Action
        with pytest.raises(httpx.RequestError) as exc_info:
            step.execute(data)
        # Assert
        assert "Error occurred" in str(exc_info.value)
        mock_check_response.assert_called_once_with(mock_response)


class TestPrintColoredTableStep:
    @patch("cli.functions.pipelines.print_colored_table")
    def test_execute_print_table_with_results(self, mock_print_table):
        # Setup
        step = pipelines.PrintColoredTableStep(key="test_results")
        data = {
            "test_results": [{"id": 1, "name": "Item1"}, {"id": 2, "name": "Item2"}]
        }
        # Action
        result = step.execute(data)
        # Assert
        assert result == data
        mock_print_table.assert_called_once_with(data["test_results"])

    @patch("cli.functions.pipelines.print_colored_table")
    def test_execute_no_key_in_data(self, mock_print_table):
        # Setup
        step = pipelines.PrintColoredTableStep(key="nonexistent_key")
        data = {
            "test_results": [{"id": 1, "name": "Item1"}, {"id": 2, "name": "Item2"}]
        }
        # Action
        result = step.execute(data)
        # Assert
        assert result == data
        mock_print_table.assert_not_called()

    @patch("cli.functions.pipelines.print_colored_table")
    def test_execute_empty_key_skips_print(self, mock_print_table):
        # Setup
        step = pipelines.PrintColoredTableStep(key="")
        data = {
            "test_results": [{"id": 1, "name": "Item1"}, {"id": 2, "name": "Item2"}]
        }
        # Action
        result = step.execute(data)
        # Assert
        assert result == data
        mock_print_table.assert_not_called()


class TestPrintkeyStep:
    @patch("typer.echo")
    def test_execute_print_key_exists(self, mock_echo):
        # Setup
        step = pipelines.PrintkeyStep(key="message")
        data = {"message": "Hello, World!"}
        # Action
        result = step.execute(data)
        # Assert
        assert result == data
        mock_echo.assert_called_once_with("Hello, World!")

    @patch("typer.echo")
    def test_execute_key_not_in_data(self, mock_echo):
        # Setup
        step = pipelines.PrintkeyStep(key="nonexistent_key")
        data = {"message": "Hello, World!"}
        # Action
        result = step.execute(data)
        # Assert
        assert result == data
        mock_echo.assert_not_called()

    @patch("typer.echo")
    def test_execute_empty_key_skips_print(self, mock_echo):
        # Setup
        step = pipelines.PrintkeyStep(key="")
        data = {"message": "Hello, World!"}
        # Action
        result = step.execute(data)
        # Assert
        assert result == data
        mock_echo.assert_not_called()
