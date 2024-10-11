from unittest import TestCase
from unittest.mock import patch

from typer.testing import CliRunner

from cli.commons.enums import DefaultInstanceFieldEnum
from cli.functions.commands import app as function_app
from cli.functions.enums import FunctionMethodEnum
from cli.functions.enums import FunctionRuntimeLayerTypeEnum

runner = CliRunner()


@patch("cli.functions.commands.get_instance_key")
@patch("cli.functions.handlers.delete_function")
class TestDeleteFunctionCommand(TestCase):
    def test_delete_function_by_id(self, mock_delete_function, mock_get_instance_key):
        mock_get_instance_key.return_value = "function_key_from_id"
        result = runner.invoke(function_app, ["delete", "--id", "function123"])
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id="function123", label=None)
        mock_delete_function.assert_called_once_with(
            function_key="function_key_from_id"
        )

    def test_delete_function_by_label(
        self, mock_delete_function, mock_get_instance_key
    ):
        mock_get_instance_key.return_value = "function_key_from_label"
        result = runner.invoke(function_app, ["delete", "--label", "functionLabel"])
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id=None, label="functionLabel")
        mock_delete_function.assert_called_once_with(
            function_key="function_key_from_label"
        )

    def test_delete_function_both_id_and_label(
        self, mock_delete_function, mock_get_instance_key
    ):
        # Setup
        mock_get_instance_key.return_value = "function_key_from_id"
        # Action
        result = runner.invoke(
            function_app, ["delete", "--id", "function123", "--label", "functionLabel"]
        )
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(
            id="function123", label="functionLabel"
        )
        mock_delete_function.assert_called_once_with(
            function_key="function_key_from_id"
        )


@patch("cli.functions.commands.get_instance_key")
@patch("cli.functions.handlers.retrieve_function")
class TestGetFunctionCommand(TestCase):
    def test_get_function_by_id(self, mock_retrieve_function, mock_get_instance_key):
        mock_get_instance_key.return_value = "function_key_from_id"
        result = runner.invoke(function_app, ["get", "--id", "function123"])
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id="function123", label=None)
        mock_retrieve_function.assert_called_once_with(
            function_key="function_key_from_id",
            fields=DefaultInstanceFieldEnum.get_default_fields(),
        )

    def test_get_function_with_custom_fields(
        self, mock_retrieve_function, mock_get_instance_key
    ):
        mock_get_instance_key.return_value = "function_key_from_id"
        custom_fields = "runtime,cron"
        result = runner.invoke(
            function_app, ["get", "--id", "function123", "--fields", custom_fields]
        )
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id="function123", label=None)
        mock_retrieve_function.assert_called_once_with(
            function_key="function_key_from_id", fields=custom_fields
        )

    def test_get_function_both_id_and_label(
        self, mock_retrieve_function, mock_get_instance_key
    ):
        # Setup
        mock_get_instance_key.return_value = "function_key_from_id"
        # Action
        result = runner.invoke(
            function_app, ["get", "--id", "function123", "--label", "functionLabel"]
        )
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(
            id="function123", label="functionLabel"
        )
        mock_retrieve_function.assert_called_once_with(
            function_key="function_key_from_id",
            fields=DefaultInstanceFieldEnum.get_default_fields(),
        )


@patch("cli.functions.handlers.list_functions")
class TestListFunctionsCommand(TestCase):
    def test_list_functions_with_defaults(self, mock_list_functions):
        result = runner.invoke(function_app, ["list"])
        self.assertEqual(result.exit_code, 0)
        mock_list_functions.assert_called_once_with(
            fields=DefaultInstanceFieldEnum.get_default_fields(),
            filter=None,
            sort_by=None,
            page_size=None,
            page=None,
        )

    def test_list_functions_with_custom_options(self, mock_list_functions):
        custom_fields = "runtime,raw"
        filter_value = "isActive=true"
        sort_by_value = "created_at"
        page_size_value = 10
        page_value = 2
        result = runner.invoke(
            function_app,
            [
                "list",
                "--fields",
                custom_fields,
                "--filter",
                filter_value,
                "--sort-by",
                sort_by_value,
                "--page-size",
                str(page_size_value),
                "--page",
                str(page_value),
            ],
        )
        self.assertEqual(result.exit_code, 0)
        mock_list_functions.assert_called_once_with(
            fields=custom_fields,
            filter=filter_value,
            sort_by=sort_by_value,
            page_size=page_size_value,
            page=page_value,
        )


@patch("cli.functions.handlers.add_function")
class TestAddFunctionCommand(TestCase):
    def test_add_function_with_minimum_arguments(self, mock_add_function):
        result = runner.invoke(function_app, ["add", "TestFunction"])
        self.assertEqual(result.exit_code, 0)
        mock_add_function.assert_called_once_with(
            name="TestFunction",
            label="",
            triggers={
                "httpMethods": [FunctionMethodEnum.get_default_method()],
                "httpHasCors": False,
                "schedulerCron": "* * * * *",
            },
            serverless={
                "runtime": FunctionRuntimeLayerTypeEnum.NODEJS_20_LITE,
                "isRawFunction": False,
                "authToken": None,
            },
            environment=[],
        )

    def test_add_function_with_all_options(self, mock_add_function):
        result = runner.invoke(
            function_app,
            [
                "add",
                "UpdatedFunction",
                "--label",
                "functionLabel",
                "--runtime",
                "python3.9:base",
                "--raw",
                "--token",
                "some_token",
                "--methods",
                "GET,POST",
                "--cors",
                "--cron",
                "*/5 * * * *",
                "--environment",
                '[{"ENV_VAR": "value"}]',
            ],
        )
        self.assertEqual(result.exit_code, 0)
        mock_add_function.assert_called_once_with(
            name="UpdatedFunction",
            label="functionLabel",
            triggers={
                "httpMethods": [FunctionMethodEnum.GET, FunctionMethodEnum.POST],
                "httpHasCors": True,
                "schedulerCron": "*/5 * * * *",
            },
            serverless={
                "runtime": FunctionRuntimeLayerTypeEnum.PYTHON_3_9_BASE,
                "isRawFunction": True,
                "authToken": "some_token",
            },
            environment=[{"ENV_VAR": "value"}],
        )


@patch("cli.functions.commands.get_instance_key")
@patch("cli.functions.handlers.update_function")
class TestUpdateFunctionCommand(TestCase):
    def test_update_function_with_minimum_arguments(
        self, mock_update_function, mock_get_instance_key
    ):
        mock_get_instance_key.return_value = "function_key_from_id"
        result = runner.invoke(function_app, ["update", "--id", "function123"])
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id="function123", label=None)
        mock_update_function.assert_called_once_with(
            function_key="function_key_from_id",
            label="",
            name="",
            triggers={
                "httpMethods": [FunctionMethodEnum.get_default_method()],
                "httpHasCors": False,
                "schedulerCron": "* * * * *",
            },
            serverless={
                "runtime": FunctionRuntimeLayerTypeEnum.NODEJS_20_LITE,
                "isRawFunction": False,
                "authToken": None,
            },
            environment=[],
        )

    def test_update_function_with_all_options(
        self, mock_update_function, mock_get_instance_key
    ):
        mock_get_instance_key.return_value = "function_key_from_label"
        result = runner.invoke(
            function_app,
            [
                "update",
                "--id",
                "function123",
                "--new-label",
                "newLabel",
                "--new-name",
                "NewFunction",
                "--runtime",
                "python3.9:lite",
                "--raw",
                "--token",
                "new_token",
                "--methods",
                "GET,POST",
                "--cors",
                "--cron",
                "0 0 * * *",
                "--environment",
                '[{"new_key": "new_value"}]',
            ],
        )
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id="function123", label=None)
        mock_update_function.assert_called_once_with(
            function_key="function_key_from_label",
            label="newLabel",
            name="NewFunction",
            triggers={
                "httpMethods": [FunctionMethodEnum.GET, FunctionMethodEnum.POST],
                "httpHasCors": True,
                "schedulerCron": "0 0 * * *",
            },
            serverless={
                "runtime": FunctionRuntimeLayerTypeEnum.PYTHON_3_9_LITE,
                "isRawFunction": True,
                "authToken": "new_token",
            },
            environment=[{"new_key": "new_value"}],
        )
