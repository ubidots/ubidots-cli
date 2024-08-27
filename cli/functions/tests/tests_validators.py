import pytest
from typer.testing import CliRunner

from cli.functions.commands import app as function_app
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.enums import FunctionPythonRuntimeLayerTypeEnum


class TestFunctionNewCommandValidators:
    @pytest.fixture(autouse=True)
    def setup(self, mocker):
        self.mocker = mocker
        self.runner = CliRunner()

    def test_folder_exists(self):
        # Setup
        self.mocker.patch("pathlib.Path.exists", return_value=True)
        self.mocker.patch.object(
            FunctionLanguageEnum, "choose", return_value=FunctionLanguageEnum.PYTHON
        )
        self.mocker.patch.object(
            FunctionLanguageEnum,
            "choose_runtime",
            return_value=FunctionPythonRuntimeLayerTypeEnum.PYTHON_3_9_FULL,
        )
        # Action
        result = self.runner.invoke(function_app, ["new", "my_function", "-i"])
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
        self.mocker.patch.object(
            FunctionLanguageEnum,
            "choose_runtime",
            return_value=FunctionPythonRuntimeLayerTypeEnum.PYTHON_3_9_FULL,
        )
        self.mocker.patch("pathlib.Path.exists", return_value=False)
        # Action
        result = self.runner.invoke(function_app, ["new", "my_function", "-i"])
        # Assert
        assert (
            f"Template for '{FunctionLanguageEnum.PYTHON}' not found at"
            in result.output
        )
        assert result.exit_code == 1
