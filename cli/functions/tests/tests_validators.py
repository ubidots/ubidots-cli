from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.commons.utils_tests import override_settings
from cli.functions.commands import app as function_app
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.models import FunctionInfo
from cli.functions.models import FunctionProjectInfo
from cli.functions.models import FunctionProjectMetadata
from cli.functions.validators import FunctionProjectValidator
from cli.settings import settings


class TestFunctionNewCommandValidators:
    @pytest.fixture(autouse=True)
    def setup(self, mocker):
        self.mocker = mocker
        self.runner = CliRunner()

    def test_folder_exists(self):
        # Setup
        self.mocker.patch("pathlib.Path.exists", return_value=True)
        # Action
        result = self.runner.invoke(function_app, ["new", "my_function"])
        # Assert
        assert "A folder named 'my_function' already exists." in result.output
        assert result.exit_code == 1

    def test_template_not_found(self):
        # Setup
        self.mocker.patch(
            "pathlib.Path.exists", lambda path: "A folder named" not in str(path)
        )
        self.mocker.patch.object(
            FunctionLanguageEnum, "choose", return_value=FunctionLanguageEnum.PYTHON
        )
        self.mocker.patch("pathlib.Path.exists", return_value=False)
        # Action
        result = self.runner.invoke(function_app, ["new", "my_function"])
        # Assert
        assert (
            f"Template for '{FunctionLanguageEnum.PYTHON.value}' not found at"
            in result.output
        )
        assert result.exit_code == 1


class TestFunctionProjectValidators:
    @pytest.fixture(autouse=True)
    def setup(self, mocker):
        self.mocker = mocker
        self.project_path = Path("/my_function")
        self.project_metadata = FunctionProjectMetadata(
            project=FunctionProjectInfo(
                name="my_function", language=FunctionLanguageEnum.PYTHON
            ),
            function=FunctionInfo(id="12345678"),
        )
        self.project_files = [Path("main.py"), Path("manifest.yaml")]

    def mock_os_walk(self, project_path: str, file_names: list):
        return [(project_path, [], file_names)]

    def mock_getsize(self, oversized_files, oversized_size):
        def getsize(path):
            if any(oversized_file in str(path) for oversized_file in oversized_files):
                return oversized_size
            return 1

        return getsize

    def test_validate_manifest_file(self):
        # Setup
        project_metadata = FunctionProjectMetadata(
            project=FunctionProjectInfo(
                name="my_function", language=FunctionLanguageEnum.PYTHON
            ),
            function=FunctionInfo(id=None),
        )
        project_files = [Path("main.py")]
        validator = FunctionProjectValidator(
            project_metadata=project_metadata, project_files=project_files
        )
        # Action & Assert
        with pytest.raises(ValueError):
            validator.validate_manifest_file()

    def test_main_file_presence_not_exist(self):
        # Setup
        project_files = [Path("hello.py")]
        validator = FunctionProjectValidator(
            project_metadata=self.project_metadata, project_files=project_files
        )
        # Action & Assert
        with pytest.raises(FileNotFoundError):
            validator.validate_main_file_presence()

    def test_validate_file_names(self):
        # Setup
        project_files = [Path("../archivo.txt"), Path("subdir\\archivo.txt")]
        validator = FunctionProjectValidator(
            project_metadata=self.project_metadata, project_files=project_files
        )
        # Action & Assert
        with pytest.raises(ValueError):
            validator.validate_file_names()

    @override_settings(obj="FUNCTIONS", ZIP_FILE__MAX_FILES_ALLOWED=2)
    def test_validate_file_count(self):
        # Setup
        project_files = [Path("file_1.py"), Path("file_2.py"), Path("file_3.py")]
        validator = FunctionProjectValidator(
            project_metadata=self.project_metadata, project_files=project_files
        )
        # Action & Assert
        with pytest.raises(ValueError):
            validator.validate_file_count()

    @override_settings(obj="FUNCTIONS", ZIP_FILE__DEFAULT_MAX_FILE_SIZE=100)
    def test_validate_individual_file_size(self):
        # Setup
        project_files = [Path("file_within_limit.py"), Path("file_exceeds_limit.py")]
        validator = FunctionProjectValidator(
            project_metadata=self.project_metadata, project_files=project_files
        )
        self.mocker.patch(
            "os.walk", lambda path: self.mock_os_walk(self.project_path, project_files)
        )
        oversized_size = settings.FUNCTIONS.ZIP_FILE.DEFAULT_MAX_FILE_SIZE + 1
        getsize_mock = self.mock_getsize(["file_exceeds_limit.py"], oversized_size)
        self.mocker.patch("os.path.getsize", getsize_mock)
        # Action & Assert
        with pytest.raises(ValueError):
            validator.validate_individual_file_size()
