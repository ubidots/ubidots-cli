from unittest import TestCase
from unittest.mock import patch

from typer.testing import CliRunner

from cli.commons.enums import DefaultInstanceFieldEnum
from cli.functions.commands import app as function_app
from cli.functions.engines.settings import engine_settings
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.enums import FunctionMethodEnum
from cli.functions.enums import FunctionRuntimeLayerTypeEnum
from cli.settings import settings

runner = CliRunner()


@patch("cli.functions.commands.get_instance_key")
@patch("cli.functions.handlers.delete_function")
class TestDeleteFunctionCommand(TestCase):
    def test_delete_function_by_id(self, mock_delete_function, mock_get_instance_key):
        # Setup
        mock_get_instance_key.return_value = "function_key_from_id"
        # Action
        result = runner.invoke(function_app, ["delete", "--id", "function123"])
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id="function123", label=None)
        mock_delete_function.assert_called_once_with(
            function_key="function_key_from_id"
        )

    def test_delete_function_by_label(
        self, mock_delete_function, mock_get_instance_key
    ):
        # Setup
        mock_get_instance_key.return_value = "function_key_from_label"
        # Action
        result = runner.invoke(function_app, ["delete", "--label", "functionLabel"])
        # Expected
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
        # Setup
        mock_get_instance_key.return_value = "function_key_from_id"
        # Action
        result = runner.invoke(function_app, ["get", "--id", "function123"])
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id="function123", label=None)
        mock_retrieve_function.assert_called_once_with(
            function_key="function_key_from_id",
            fields=DefaultInstanceFieldEnum.get_default_fields(),
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )

    def test_get_function_with_custom_fields(
        self, mock_retrieve_function, mock_get_instance_key
    ):
        # Setup
        mock_get_instance_key.return_value = "function_key_from_id"
        custom_fields = "runtime,cron"
        # Action
        result = runner.invoke(
            function_app, ["get", "--id", "function123", "--fields", custom_fields]
        )
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id="function123", label=None)
        mock_retrieve_function.assert_called_once_with(
            function_key="function_key_from_id",
            fields=custom_fields,
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
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
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )


@patch("cli.functions.handlers.list_functions")
class TestListFunctionsCommand(TestCase):
    def test_list_functions_with_defaults(self, mock_list_functions):
        # Action
        result = runner.invoke(function_app, ["list"])
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_list_functions.assert_called_once_with(
            fields=DefaultInstanceFieldEnum.get_default_fields(),
            filter=None,
            sort_by=None,
            page_size=None,
            page=None,
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )

    def test_list_functions_with_custom_options(self, mock_list_functions):
        # Setup
        custom_fields = "runtime,raw"
        filter_value = "isActive=true"
        sort_by_value = "created_at"
        page_size_value = 10
        page_value = 2
        # Action
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
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_list_functions.assert_called_once_with(
            fields=custom_fields,
            filter=filter_value,
            sort_by=sort_by_value,
            page_size=page_size_value,
            page=page_value,
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )


@patch("cli.functions.handlers.add_function")
class TestAddFunctionCommand(TestCase):
    def test_add_function_with_minimum_arguments(self, mock_add_function):
        # Action
        result = runner.invoke(function_app, ["add", "TestFunction"])
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_add_function.assert_called_once_with(
            name="TestFunction",
            label="",
            triggers={
                "httpMethods": [FunctionMethodEnum.get_default_method()],
                "httpHasCors": False,
                "schedulerCron": "",
            },
            serverless={
                "runtime": FunctionRuntimeLayerTypeEnum.NODEJS_20_LITE,
                "isRawFunction": False,
                "authToken": None,
            },
            environment=[],
        )

    def test_add_function_with_all_options(self, mock_add_function):
        # Action
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
        # Expected
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
        # Setup
        mock_get_instance_key.return_value = "function_key_from_id"
        # Action
        result = runner.invoke(function_app, ["update", "--id", "function123"])
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id="function123", label=None)
        mock_update_function.assert_called_once_with(
            function_key="function_key_from_id",
            label="",
            name="",
            triggers={
                "httpMethods": [FunctionMethodEnum.get_default_method()],
                "httpHasCors": False,
                "schedulerCron": "",
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
        # Setup
        mock_get_instance_key.return_value = "function_key_from_label"
        # Action
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
        # Expected
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


@patch("cli.functions.commands.executor.create_function")
class TestNewFunctionCommand(TestCase):
    def test_new_function_with_defaults(self, mock_create_function):
        # Action
        result = runner.invoke(function_app, ["new"])
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_create_function.assert_called_once_with(
            name=settings.FUNCTIONS.DEFAULT_PROJECT_NAME,
            language=FunctionLanguageEnum.NODEJS,
            runtime=FunctionRuntimeLayerTypeEnum.NODEJS_20_LITE,
            methods=FunctionMethodEnum.parse_methods_to_enum_list(
                FunctionMethodEnum.get_default_method()
            ),
            is_raw=settings.FUNCTIONS.DEFAULT_IS_RAW,
            cron=settings.FUNCTIONS.DEFAULT_CRON,
            cors=settings.FUNCTIONS.DEFAULT_HAS_CORS,
            verbose=False,
        )

    def test_new_function_with_custom_options(self, mock_create_function):
        # Action
        result = runner.invoke(
            function_app,
            [
                "new",
                "--name",
                "CustomFunction",
                "--runtime",
                "python3.9:base",
                "--raw",
                "--cors",
                "--cron",
                "0 0 * * *",
                "--methods",
                "GET,POST",
                "--verbose",
            ],
        )
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_create_function.assert_called_once_with(
            name="CustomFunction",
            language=FunctionLanguageEnum.PYTHON,
            runtime=FunctionRuntimeLayerTypeEnum.PYTHON_3_9_BASE,
            methods=[FunctionMethodEnum.GET, FunctionMethodEnum.POST],
            is_raw=True,
            cron="0 0 * * *",
            cors=True,
            verbose=True,
        )

    def test_new_function_interactive_mode(self, mock_create_function):
        with patch("cli.functions.commands.inquirer") as mock_inquirer:
            # Setup
            mock_inquirer.text.return_value.execute.side_effect = [
                "InteractiveFunction",
                settings.FUNCTIONS.DEFAULT_CRON,
            ]
            mock_inquirer.select.return_value.execute.side_effect = [
                FunctionLanguageEnum.PYTHON,
                FunctionRuntimeLayerTypeEnum.PYTHON_3_9_BASE,
            ]
            mock_inquirer.checkbox.return_value.execute.return_value = [
                FunctionMethodEnum.GET,
                FunctionMethodEnum.POST,
            ]
            mock_inquirer.confirm.return_value.execute.side_effect = [True, True]
            # Action
            result = runner.invoke(function_app, ["new", "--interactive"])
            # Expected
            self.assertEqual(result.exit_code, 0)
            mock_create_function.assert_called_once_with(
                name="InteractiveFunction",
                language=FunctionLanguageEnum.PYTHON,
                runtime=FunctionRuntimeLayerTypeEnum.PYTHON_3_9_BASE,
                methods=[FunctionMethodEnum.GET, FunctionMethodEnum.POST],
                is_raw=True,
                cron=settings.FUNCTIONS.DEFAULT_CRON,
                cors=True,
                verbose=False,
            )


@patch("cli.functions.commands.executor.start_function")
class TestStartFunctionCommand(TestCase):
    def test_start_function_with_defaults(self, mock_start_function):
        # Action
        result = runner.invoke(function_app, ["start"])
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_start_function.assert_called_once_with(
            engine=engine_settings.CONTAINER.DEFAULT_ENGINE,
            methods=None,
            is_raw=None,
            token="",
            cors=None,
            cron=settings.FUNCTIONS.DEFAULT_CRON,
            timeout=settings.FUNCTIONS.DEFAULT_TIMEOUT_SECONDS,
            verbose=False,
        )

    def test_start_function_with_custom_options(self, mock_start_function):
        # Action
        result = runner.invoke(
            function_app,
            [
                "start",
                "--engine",
                f"{engine_settings.CONTAINER.DEFAULT_ENGINE}",
                "--methods",
                "GET,POST",
                "--raw",
                "--cors",
                "--cron",
                "*/5 * * * *",
                "--timeout",
                "120",
                "--token",
                "custom_token",
                "--verbose",
            ],
        )
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_start_function.assert_called_once_with(
            engine=engine_settings.CONTAINER.DEFAULT_ENGINE,
            methods=[FunctionMethodEnum.GET, FunctionMethodEnum.POST],
            is_raw=True,
            token="custom_token",
            cors=True,
            cron="*/5 * * * *",
            timeout=120,
            verbose=True,
        )


@patch("cli.functions.commands.executor.stop_function")
class TestStopFunctionCommand(TestCase):
    def test_stop_function_with_defaults(self, mock_stop_function):
        # Action
        result = runner.invoke(function_app, ["stop"])
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_stop_function.assert_called_once_with(
            engine=engine_settings.CONTAINER.DEFAULT_ENGINE,
            label="",
            verbose=False,
        )

    def test_stop_function_with_custom_options(self, mock_stop_function):
        # Action
        result = runner.invoke(function_app, ["stop", "--label", "test_function"])
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_stop_function.assert_called_once_with(
            engine=engine_settings.CONTAINER.DEFAULT_ENGINE,
            label="test_function",
            verbose=False,
        )


@patch("cli.functions.commands.executor.restart_function")
class TestRestartFunctionCommand(TestCase):
    def test_restart_function_with_defaults(self, mock_restart_function):
        # Action
        result = runner.invoke(function_app, ["restart"])
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_restart_function.assert_called_once_with(
            engine=engine_settings.CONTAINER.DEFAULT_ENGINE,
            verbose=False,
        )


@patch("cli.functions.commands.executor.status_function")
class TestStatusFunctionCommand(TestCase):
    def test_status_function_with_defaults(self, mock_status_function):
        # Action
        result = runner.invoke(function_app, ["status"])
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_status_function.assert_called_once_with(
            engine=engine_settings.CONTAINER.DEFAULT_ENGINE,
            verbose=False,
        )


@patch("cli.functions.commands.executor.logs_function")
class TestLogsFunctionCommand(TestCase):
    def test_logs_function_with_defaults(self, mock_logs_function):
        # Action
        result = runner.invoke(function_app, ["logs", "test_function"])
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_logs_function.assert_called_once_with(
            engine=engine_settings.CONTAINER.DEFAULT_ENGINE,
            label="test_function",
            tail="all",
            follow=False,
            remote=False,
            verbose=False,
        )

    def test_logs_function_with_custom_options(self, mock_logs_function):
        # Action
        result = runner.invoke(
            function_app,
            [
                "logs",
                "test_function",
                "--follow",
                "--remote",
                "--tail",
                "100",
                "--verbose",
            ],
        )
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_logs_function.assert_called_once_with(
            engine=engine_settings.CONTAINER.DEFAULT_ENGINE,
            label="test_function",
            tail="100",
            follow=True,
            remote=True,
            verbose=True,
        )


@patch("cli.functions.commands.executor.push_function")
class TestPushFunctionCommand(TestCase):
    def test_push_function_with_defaults(self, mock_push_function):
        # Action
        result = runner.invoke(function_app, ["push"])
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_push_function.assert_called_once_with(
            confirm=False,
            verbose=False,
        )

    def test_push_function_with_confirmation(self, mock_push_function):
        # Action
        result = runner.invoke(function_app, ["push", "--yes", "--verbose"])
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_push_function.assert_called_once_with(
            confirm=True,
            verbose=True,
        )


@patch("cli.functions.commands.executor.pull_function")
class TestPullFunctionCommand(TestCase):
    def test_pull_function_with_defaults(self, mock_pull_function):
        # Action
        result = runner.invoke(function_app, ["pull"])
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_pull_function.assert_called_once_with(
            confirm=False,
            verbose=False,
        )

    def test_pull_function_with_confirmation(self, mock_pull_function):
        # Action
        result = runner.invoke(function_app, ["pull", "--yes", "--verbose"])
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_pull_function.assert_called_once_with(
            confirm=True,
            verbose=True,
        )
