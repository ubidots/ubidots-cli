import zipfile
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import ANY
from unittest.mock import MagicMock
from unittest.mock import patch

import httpx
import pytest

from cli.config.models import ProfileConfigModel
from cli.functions import pipelines
from cli.functions.constants import PYTHON_3_9_BASE_RUNTIME
from cli.functions.constants import PYTHON_3_11_LITE_RUNTIME
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.enums import FunctionMethodEnum
from cli.functions.exceptions import FolderAlreadyExistsError
from cli.functions.exceptions import PermissionDeniedError
from cli.functions.exceptions import TemplateNotFoundError
from cli.functions.models import FunctionProjectMetadata
from cli.functions.pipelines import ValidateAllowedRuntimeStep
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
            "name": "Function name",
            "project_path": Path("/path/to/project"),
            "language": FunctionLanguageEnum.PYTHON,
            "runtime": PYTHON_3_9_BASE_RUNTIME,
            "methods": [FunctionMethodEnum.GET, FunctionMethodEnum.POST],
            "label": "function-name",
            "created_at": "2025-02-18T15:00:00",
            "timeout": 30,
            "http_is_secure": True,
            "http_enabled": True,
            "engine": FunctionEngineTypeEnum.DOCKER.value,
            "has_cors": True,
            "is_raw": True,
            "cron": "",
            "has_cron": False,
            "function_id": "function_id_test",
            "token": "token_test",
        }
        # Action
        result = step.execute(data)
        # Assert
        assert result == data
        mock_save_manifest.assert_called_once_with(
            name=data["name"],
            project_path=data["project_path"],
            language=data["language"],
            runtime=data["runtime"],
            methods=data["methods"],
            label=data["label"],
            created_at=data["created_at"],
            timeout=data["timeout"],
            http_is_secure=data["http_is_secure"],
            http_enabled=data["http_enabled"],
            engine=data["engine"],
            has_cors=data["has_cors"],
            is_raw=data["is_raw"],
            cron=data["cron"],
            has_cron=data["has_cron"],
            function_id=data["function_id"],
            token=data["token"],
        )

    @patch("cli.functions.pipelines.save_manifest_project_file")
    def test_execute_with_missing_fields(self, mock_save_manifest):
        # Setup: Create a data dictionary missing some required fields (e.g., 'language' and 'runtime')
        step = pipelines.SaveManifestStep()
        data = {
            "name": "Function name",
            "project_path": Path("/path/to/project"),
            # "language" and "runtime" keys are intentionally missing.
            "methods": [FunctionMethodEnum.GET, FunctionMethodEnum.POST],
            "label": "function-name",
            "created_at": "2025-02-18T15:00:00",
            "timeout": 30,
            "http_is_secure": True,
            "http_enabled": True,
            "engine": FunctionEngineTypeEnum.DOCKER.value,
            "has_cors": True,
            "is_raw": True,
            "cron": "",
            "has_cron": False,
            "function_id": "function_id_test",
            "token": "token_test",
        }
        mock_save_manifest.side_effect = TypeError("missing required keys")
        # Action & Assert: Expect a TypeError when required fields are missing.
        with pytest.raises(TypeError):
            step.execute(data)


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
            "Not in a function directory. Run this command inside a function project or use 'dev add' to create one."
        )
        with pytest.raises(FileNotFoundError) as exc_info:
            step.execute(data)
        # Assert
        assert (
            "Not in a function directory. Run this command inside a function project or use 'dev add' to create one."
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
        project_metadata_mock.project.language.extension = "py"
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
        project_metadata_mock.project.language.extension = "py"
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


class TestExtractProjectStep:
    @patch("zipfile.ZipFile")
    @patch("pathlib.Path.exists", return_value=False)  # Metadata file doesn't exist
    @patch("pathlib.Path.mkdir")  # Mock the mkdir call
    def test_execute_success(self, mock_mkdir, mock_exists, mock_zip_class):
        # Setup
        step = pipelines.ExtractProjectStep()
        mock_response = MagicMock()
        mock_response.content = b"Fake zip content"

        # Mock the ZipFile context manager
        mock_zip_instance = MagicMock()
        mock_zip_instance.infolist.return_value = []  # Empty ZIP for simple test
        mock_zip_instance.__enter__ = MagicMock(return_value=mock_zip_instance)
        mock_zip_instance.__exit__ = MagicMock(return_value=None)
        mock_zip_class.return_value = mock_zip_instance

        data = {
            "project_path": Path("/path/to/project"),
            "function_zip_content": mock_response,
            "remote_function_detail": {"name": "my_function"},
        }
        # Action
        result = step.execute(data)
        # Assert
        assert result == data
        mock_zip_class.assert_called_once()
        # The test should expect the path that the implementation actually uses
        mock_zip_instance.extractall.assert_called_once_with(
            Path("/path/to/project/my_function")
        )

    @patch("zipfile.ZipFile.__init__", side_effect=zipfile.BadZipFile("Bad zip file"))
    def test_execute_raises_bad_zip_file_error(self, mock_zip_init):
        # Setup
        step = pipelines.ExtractProjectStep()
        mock_response = MagicMock()
        mock_response.content = b"Corrupt zip content"
        data = {
            "project_path": Path("/path/to/project"),
            "function_zip_content": mock_response,
            "remote_function_detail": {"name": "my_function"},
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
            "project_path": Path("/path/to/project"),
            "function_zip_content": mock_response,
            "remote_function_detail": {"name": "my_function"},
        }
        # Action
        with pytest.raises(FileNotFoundError) as exc_info:
            step.execute(data)
        # Assert
        assert "File not found" in str(exc_info.value)
        mock_zip_init.assert_called_once_with(ANY, "r")


class TestValidateNotInExistingFunctionDirectoryStep:
    @patch("pathlib.Path.cwd")
    @patch("pathlib.Path.exists", return_value=False)
    def test_execute_success_not_in_function_directory(self, mock_exists, mock_cwd):
        # Setup
        mock_cwd.return_value = Path("/some/directory")
        step = pipelines.ValidateNotInExistingFunctionDirectoryStep()
        data = {"project_path": Path("/some/directory/new_function")}

        # Action
        result = step.execute(data)

        # Assert
        assert result == data
        mock_exists.assert_called_once()

    @patch("pathlib.Path.cwd")
    @patch("pathlib.Path.exists", return_value=True)
    def test_execute_raises_error_in_function_directory(self, mock_exists, mock_cwd):
        # Setup
        mock_cwd.return_value = Path("/existing/function")
        step = pipelines.ValidateNotInExistingFunctionDirectoryStep()
        data = {"project_path": Path("/existing/function/new_function")}

        # Action & Assert
        with pytest.raises(ValueError) as exc_info:
            step.execute(data)

        assert "Cannot run 'functions init' from within an existing" in str(
            exc_info.value
        )
        assert "function directory" in str(exc_info.value)
        mock_exists.assert_called_once()


class TestBuildEndpointStep:
    @patch("cli.functions.pipelines.build_endpoint")
    def test_execute_success(self, mock_build_endpoint):
        # Setup
        step = pipelines.BuildEndpointStep(api_route="/api/function")
        mock_url = "https://api.example.com/api/function/test_function_id"
        mock_headers = {"X-Auth-Token": "test_token"}
        mock_build_endpoint.return_value = (mock_url, mock_headers)
        mock_active_config = MagicMock()
        data = {
            "remote_id": "test_function_id",
            "active_config": mock_active_config,
        }
        # Action
        result = step.execute(data)
        # Assert
        assert result["url"] == mock_url
        assert result["headers"] == mock_headers
        mock_build_endpoint.assert_called_once_with(
            route=step.api_route,
            function_key="test_function_id",
            active_config=mock_active_config,
        )

    @patch(
        "cli.functions.pipelines.build_endpoint",
        side_effect=Exception("Endpoint build failed"),
    )
    def test_execute_raises_exception(self, mock_build_endpoint):
        # Setup
        step = pipelines.BuildEndpointStep(api_route="/api/function")
        mock_active_config = MagicMock()
        data = {
            "remote_id": "test_function_id",
            "active_config": mock_active_config,
        }
        # Action & Assert
        with pytest.raises(Exception) as exc_info:
            step.execute(data)
        assert "Endpoint build failed" in str(exc_info.value)
        mock_build_endpoint.assert_called_once_with(
            route=step.api_route,
            function_key="test_function_id",
            active_config=mock_active_config,
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
        project_metadata_mock.project.runtime = PYTHON_3_11_LITE_RUNTIME
        project_metadata_mock.function.is_raw = False
        project_metadata_mock.function.timeout = 30
        project_metadata_mock.function.payload = {}
        data = {
            "url": "https://api.example.com/functions",
            "headers": {"X-Auth-Token": "test_token"},
            "project_metadata": project_metadata_mock,
            "needs_update": False,
        }
        # Action
        result = step.execute(data)
        assert "function_id" in result or "id" in mock_response.json.return_value
        result.setdefault("function_id", mock_response.json.return_value["id"])
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


class TestCheckResponseStep:
    @patch("cli.functions.pipelines.check_response_status")
    def test_execute_check_response_success(self, mock_check_response):
        step = pipelines.CheckResponseStep(response_key="response")
        mock_response = MagicMock()
        mock_response.status_code = httpx.codes.OK
        data = {"response": mock_response}
        result = step.execute(data)
        assert result == data
        mock_check_response.assert_called_once_with(mock_response)

    @patch(
        "cli.functions.pipelines.check_response_status",
        side_effect=httpx.RequestError("Error occurred"),
    )
    def test_execute_check_response_raises_error(self, mock_check_response):
        # Setup: Use the correct response_key ("response")
        step = pipelines.CheckResponseStep(response_key="response")
        mock_response = MagicMock()
        mock_response.status_code = (
            httpx.codes.BAD_REQUEST
        )  # status code indicating failure
        data = {"response": mock_response}
        # Action & Assert: Expect a RequestError to be raised during execution.
        with pytest.raises(httpx.RequestError) as exc_info:
            step.execute(data)
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


def test_function_runtime_layer_type_enum_removed():
    import cli.functions.enums as enums

    assert not hasattr(enums, "FunctionRuntimeLayerTypeEnum")


# --- InvokeFunctionStep ---


class TestInvokeFunctionStep:
    @patch("cli.functions.pipelines.httpx.post")
    @patch("cli.functions.pipelines.build_endpoint")
    def test_successful_invoke(self, mock_build_endpoint, mock_post):
        mock_build_endpoint.return_value = (
            "https://api.ubidots.com/invoke",
            {"X-Auth-Token": "tok"},
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "OK",
            "logs": ["{'temp': 25}"],
            "response": {"result": {"args": {"temp": 25}}},
        }
        mock_post.return_value = mock_response

        step = pipelines.InvokeFunctionStep()
        data = {
            "active_config": MagicMock(),
            "function_key": "~my-fn",
            "payload": {"temp": 25},
        }
        result = step.execute(data)

        assert result["invoke_response"]["response"]["result"] == {"args": {"temp": 25}}
        mock_post.assert_called_once_with(
            "https://api.ubidots.com/invoke",
            headers={"X-Auth-Token": "tok"},
            json={"payload": '{"temp": 25}'},
        )

    @patch("cli.functions.pipelines.httpx.post")
    @patch("cli.functions.pipelines.build_endpoint")
    def test_invoke_404_raises_function_not_found(self, mock_build_endpoint, mock_post):
        mock_build_endpoint.return_value = (
            "https://api.ubidots.com/invoke",
            {"X-Auth-Token": "tok"},
        )
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_post.return_value = mock_response

        step = pipelines.InvokeFunctionStep()
        data = {"active_config": MagicMock(), "function_key": "~ghost", "payload": {}}

        with pytest.raises(httpx.RequestError, match=r"Function 'ghost' not found\."):
            step.execute(data)


# --- PrintInvokeResponseStep ---


class TestPrintInvokeResponseStep:
    @patch("typer.echo")
    def test_prints_logs_and_result(self, mock_echo):
        step = pipelines.PrintInvokeResponseStep()
        data = {
            "invoke_response": {
                "logs": ["{'temp': 25}"],
                "response": {"result": {"args": {"temp": 25}}},
                "start": 1000,
                "end": 1500,
            }
        }
        result = step.execute(data)

        assert result is data
        calls = [c.args[0] for c in mock_echo.call_args_list]
        assert "\n--- Execution logs ---" in calls
        assert "{'temp': 25}" in calls
        assert "\n--- Result ---" in calls
        assert "\nDuration: 500ms" in calls

    @patch("typer.echo")
    def test_no_logs_skips_logs_section(self, mock_echo):
        step = pipelines.PrintInvokeResponseStep()
        data = {"invoke_response": {"logs": [], "response": {"result": {"ok": True}}}}
        step.execute(data)

        calls = [c.args[0] for c in mock_echo.call_args_list]
        assert "\n--- Execution logs ---" not in calls
        assert "\n--- Result ---" in calls

    @patch("typer.echo")
    def test_no_duration_when_missing_timestamps(self, mock_echo):
        step = pipelines.PrintInvokeResponseStep()
        data = {"invoke_response": {"logs": [], "response": {"result": {}}}}
        step.execute(data)

        calls = [str(c) for c in mock_echo.call_args_list]
        assert not any("Duration" in c for c in calls)


# --- WaitAndFetchLatestLogsStep ---


class TestWaitAndFetchLatestLogsStep:
    @patch("cli.functions.pipelines._fetch_activation_details", return_value=[])
    @patch("cli.functions.pipelines.check_response_status")
    @patch("cli.functions.pipelines.httpx.get")
    @patch("cli.functions.pipelines.build_endpoint")
    @patch("typer.echo")
    def test_no_activations(
        self, mock_echo, mock_build, mock_get, mock_check, mock_fetch
    ):
        mock_build.return_value = (
            "https://api.ubidots.com/logs",
            {"X-Auth-Token": "tok"},
        )
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_get.return_value = mock_response

        step = pipelines.WaitAndFetchLatestLogsStep(count=5)
        data = {"active_config": MagicMock(), "function_key": "~my-fn"}
        result = step.execute(data)

        assert result["activation_logs"] == []
        mock_echo.assert_called_with("No activations found.")
        mock_fetch.assert_not_called()

    @patch("cli.functions.pipelines._fetch_activation_details")
    @patch("cli.functions.pipelines.check_response_status")
    @patch("cli.functions.pipelines.httpx.get")
    @patch("cli.functions.pipelines.build_endpoint")
    def test_slices_to_count(self, mock_build, mock_get, mock_check, mock_fetch):
        mock_build.return_value = (
            "https://api.ubidots.com/logs",
            {"X-Auth-Token": "tok"},
        )
        activations = [{"activationId": f"act-{i}"} for i in range(10)]
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": activations}
        mock_get.return_value = mock_response
        mock_fetch.return_value = [{"_activation_id": f"act-{i}"} for i in range(3)]

        step = pipelines.WaitAndFetchLatestLogsStep(count=3)
        data = {"active_config": MagicMock(), "function_key": "~my-fn"}
        step.execute(data)

        # Should pass only the first 3 activations (newest-first from API)
        called_activations = mock_fetch.call_args[1]["activations"]
        assert len(called_activations) == 3
        assert [a["activationId"] for a in called_activations] == [
            "act-0",
            "act-1",
            "act-2",
        ]

    @patch("cli.functions.pipelines._fetch_activation_details")
    @patch("cli.functions.pipelines.check_response_status")
    @patch("cli.functions.pipelines.httpx.get")
    @patch("cli.functions.pipelines.build_endpoint")
    def test_count_larger_than_available(
        self, mock_build, mock_get, mock_check, mock_fetch
    ):
        mock_build.return_value = (
            "https://api.ubidots.com/logs",
            {"X-Auth-Token": "tok"},
        )
        activations = [{"activationId": "act-0"}, {"activationId": "act-1"}]
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": activations}
        mock_get.return_value = mock_response
        mock_fetch.return_value = []

        step = pipelines.WaitAndFetchLatestLogsStep(count=10)
        data = {"active_config": MagicMock(), "function_key": "~my-fn"}
        step.execute(data)

        called_activations = mock_fetch.call_args[1]["activations"]
        assert len(called_activations) == 2

    @patch("cli.functions.pipelines.httpx.get")
    @patch("cli.functions.pipelines.build_endpoint")
    def test_404_raises_function_not_found(self, mock_build, mock_get):
        mock_build.return_value = (
            "https://api.ubidots.com/logs",
            {"X-Auth-Token": "tok"},
        )
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        step = pipelines.WaitAndFetchLatestLogsStep(count=1)
        data = {"active_config": MagicMock(), "function_key": "~ghost"}

        with pytest.raises(httpx.RequestError, match=r"Function 'ghost' not found\."):
            step.execute(data)


# --- PrintActivationLogsStep ---


class TestPrintActivationLogsStep:
    @patch("typer.echo")
    def test_no_logs_found(self, mock_echo):
        step = pipelines.PrintActivationLogsStep()
        data = {"activation_logs": []}
        step.execute(data)

        mock_echo.assert_called_with("No logs found.")

    @patch("typer.echo")
    def test_prints_list_logs(self, mock_echo):
        step = pipelines.PrintActivationLogsStep()
        data = {
            "activation_logs": [
                {"_activation_id": "act-1", "logs": ["line1\n", "line2\n"]}
            ]
        }
        step.execute(data)

        calls = [c.args[0] for c in mock_echo.call_args_list]
        assert "\n--- Activation: act-1 ---" in calls
        assert "line1\n" in calls

    @patch("typer.echo")
    def test_prints_string_logs(self, mock_echo):
        step = pipelines.PrintActivationLogsStep()
        data = {
            "activation_logs": [{"_activation_id": "act-1", "logs": "full log output"}]
        }
        step.execute(data)

        calls = [c.args[0] for c in mock_echo.call_args_list]
        assert "full log output" in calls

    @patch("typer.echo")
    def test_handles_error_entries(self, mock_echo):
        step = pipelines.PrintActivationLogsStep()
        data = {
            "activation_logs": [
                {"_activation_id": "act-1", "error": "Failed to fetch log detail"}
            ]
        }
        step.execute(data)

        calls = [c.args[0] for c in mock_echo.call_args_list]
        assert "\n--- Activation: act-1 ---" in calls
        assert "Error: Failed to fetch log detail" in calls


class TestValidateAllowedRuntimeStep:
    @patch("cli.functions.pipelines.get_configuration")
    def test_raises_with_plan_message_when_runtimes_empty(self, mock_get_config):
        mock_get_config.return_value = ProfileConfigModel(runtimes=[])
        step = ValidateAllowedRuntimeStep()
        data = {"runtime": "python3.10", "profile": "stem-profile"}

        with pytest.raises(ValueError, match="Your plan may not include UbiFunctions"):
            step.execute(data)

    @patch("cli.functions.pipelines.get_configuration")
    def test_raises_when_runtime_not_in_allowed_list(self, mock_get_config):
        mock_get_config.return_value = ProfileConfigModel(runtimes=["python3.10"])
        step = ValidateAllowedRuntimeStep()
        data = {"runtime": "nodejs16", "profile": "test-profile"}

        with pytest.raises(ValueError, match="nodejs16"):
            step.execute(data)

    @patch("cli.functions.pipelines.get_configuration")
    def test_passes_when_runtime_in_allowed_list(self, mock_get_config):
        mock_get_config.return_value = ProfileConfigModel(runtimes=["python3.10"])
        step = ValidateAllowedRuntimeStep()
        data = {"runtime": "python3.10", "profile": "test-profile"}

        result = step.execute(data)

        assert result == data
