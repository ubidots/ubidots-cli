from unittest import TestCase
from unittest.mock import ANY
from unittest.mock import MagicMock
from unittest.mock import patch

from typer.testing import CliRunner

from cli.commons.enums import DefaultInstanceFieldEnum
from cli.settings import settings
from cli.variables.commands import app as variable_app
from cli.variables.enums import VariableTypeEnum

runner = CliRunner()


@patch("cli.variables.commands.get_configuration", return_value=MagicMock())
@patch("cli.variables.commands.get_instance_key")
@patch("cli.variables.handlers.delete_variable")
class TestDeleteCommand(TestCase):
    def test_delete_variable(self, mock_delete_variable, mock_get_instance_key, _):
        mock_get_instance_key.return_value = "variable_id"
        result = runner.invoke(variable_app, ["delete", "--id", "variable123"])
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id="variable123")
        mock_delete_variable.assert_called_once_with(
            active_config=ANY,
            variable_key="variable_id",
        )


@patch("cli.variables.commands.get_configuration", return_value=MagicMock())
@patch("cli.variables.commands.get_instance_key")
@patch("cli.variables.handlers.retrieve_variable")
class TestGetCommand(TestCase):
    def test_get_variable(self, mock_retrieve_variable, mock_get_instance_key, _):
        mock_get_instance_key.return_value = "variable_id"
        result = runner.invoke(variable_app, ["get", "--id", "variable123"])
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id="variable123")
        mock_retrieve_variable.assert_called_once_with(
            active_config=ANY,
            variable_key="variable_id",
            fields=DefaultInstanceFieldEnum.get_default_fields(),
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )

    def test_get_variable_with_custom_fields(
        self, mock_retrieve_variable, mock_get_instance_key, _
    ):
        mock_get_instance_key.return_value = "variable_id"
        custom_fields = "name,description"
        result = runner.invoke(
            variable_app, ["get", "--id", "variable123", "--fields", custom_fields]
        )
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id="variable123")
        mock_retrieve_variable.assert_called_once_with(
            active_config=ANY,
            variable_key="variable_id",
            fields=custom_fields,
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )


@patch("cli.variables.commands.get_configuration", return_value=MagicMock())
@patch("cli.variables.handlers.list_variable")
class TestListCommand(TestCase):
    def test_list_variables_with_defaults(self, mock_list_variables, _):
        result = runner.invoke(variable_app, ["list"])
        self.assertEqual(result.exit_code, 0)
        mock_list_variables.assert_called_once_with(
            active_config=ANY,
            fields=DefaultInstanceFieldEnum.get_default_fields(),
            filter=None,
            sort_by=None,
            page_size=None,
            page=None,
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )

    def test_list_variables_with_custom_fields(self, mock_list_variables, _):
        custom_fields = "name,description"
        result = runner.invoke(variable_app, ["list", "--fields", custom_fields])
        self.assertEqual(result.exit_code, 0)
        mock_list_variables.assert_called_once_with(
            active_config=ANY,
            fields=custom_fields,
            filter=None,
            sort_by=None,
            page_size=None,
            page=None,
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )


@patch("cli.variables.commands.get_configuration", return_value=MagicMock())
@patch("cli.variables.handlers.add_variable")
class TestAddCommand(TestCase):
    def test_add_variable_with_minimum_arguments(self, mock_add_variable, _):
        result = runner.invoke(variable_app, ["add", "device123", "variableLabel"])
        self.assertEqual(result.exit_code, 0)
        mock_add_variable.assert_called_once_with(
            active_config=ANY,
            label="variableLabel",
            name="",
            description="",
            device="device123",
            type=VariableTypeEnum.RAW,
            unit="",
            synthetic_expression="",
            tags="",
            properties={},
            min=None,
            max=None,
        )

    def test_add_variable_with_all_options(self, mock_add_variable, _):
        result = runner.invoke(
            variable_app,
            [
                "add",
                "device123",
                "variableLabel",
                "VariableName",
                "--description",
                "Test variable description",
                "--type",
                f"{VariableTypeEnum.SYNTHETIC}",
                "--unit",
                "C",
                "--synthetic-expression",
                "value * 2",
                "--tags",
                "tag1,tag2",
                "--properties",
                '{"key1": "value1"}',
                "--min",
                "0",
                "--max",
                "100",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        mock_add_variable.assert_called_once_with(
            active_config=ANY,
            label="variableLabel",
            name="VariableName",
            description="Test variable description",
            device="device123",
            type=VariableTypeEnum.SYNTHETIC,
            unit="C",
            synthetic_expression="value * 2",
            tags="tag1,tag2",
            properties={"key1": "value1"},
            min=0,
            max=100,
        )


@patch("cli.variables.commands.get_configuration", return_value=MagicMock())
@patch("cli.variables.commands.get_instance_key")
@patch("cli.variables.handlers.update_variable")
class TestUpdateCommand(TestCase):
    def test_update_variable_with_minimum_arguments(
        self, mock_update_variable, mock_get_instance_key, _
    ):
        mock_get_instance_key.return_value = "variable_key"
        result = runner.invoke(variable_app, ["update", "--id", "variable123"])
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id="variable123")
        mock_update_variable.assert_called_once_with(
            active_config=ANY,
            variable_key="variable_key",
            label="",
            name="",
            description="",
            type=VariableTypeEnum.RAW,
            unit="",
            synthetic_expression="",
            tags="",
            properties={},
            min=None,
            max=None,
        )

    def test_update_variable_with_all_options(
        self, mock_update_variable, mock_get_instance_key, _
    ):
        mock_get_instance_key.return_value = "variable_key"
        result = runner.invoke(
            variable_app,
            [
                "update",
                "--id",
                "variable123",
                "--new-label",
                "newVariableLabel",
                "--new-name",
                "UpdatedVariableName",
                "--description",
                "Updated description",
                "--type",
                f"{VariableTypeEnum.RAW}",
                "--unit",
                "C",
                "--synthetic-expression",
                "value * 2",
                "--tags",
                "tagA,tagB",
                "--properties",
                '{"key1": "updatedValue"}',
                "--min",
                "0",
                "--max",
                "200",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id="variable123")
        mock_update_variable.assert_called_once_with(
            active_config=ANY,
            variable_key="variable_key",
            label="newVariableLabel",
            name="UpdatedVariableName",
            description="Updated description",
            type=VariableTypeEnum.RAW,
            unit="C",
            synthetic_expression="value * 2",
            tags="tagA,tagB",
            properties={"key1": "updatedValue"},
            min=0,
            max=200,
        )

    def test_update_variable_with_invalid_json_properties(
        self, mock_update_variable, mock_get_instance_key, _
    ):
        mock_get_instance_key.return_value = "variable_key"
        result = runner.invoke(
            variable_app,
            ["update", "--id", "variable123", "--properties", "{key1: updatedValue}"],
        )
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Invalid JSON format.", result.stdout)
        mock_update_variable.assert_not_called()
