from unittest import TestCase
from unittest.mock import ANY
from unittest.mock import patch

from typer.testing import CliRunner

from cli.functions.commands import app as function_app
from cli.functions.constants import DEFAULT_RUNTIME
from cli.functions.constants import PYTHON_3_9_BASE_RUNTIME
from cli.functions.constants import PYTHON_3_9_LITE_RUNTIME
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.enums import FunctionMethodEnum
from cli.settings import settings

runner = CliRunner()


class TestDevAddFunctionCommand(TestCase):
    @patch("cli.functions.commands.executor.create_function")
    def test_dev_add_function_with_defaults(self, mock_create_function):
        # Action
        result = runner.invoke(
            function_app,
            [
                "dev",
                "add",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        mock_create_function.assert_called_once_with(
            name=settings.FUNCTIONS.DEFAULT_PROJECT_NAME,
            language=FunctionLanguageEnum(settings.FUNCTIONS.DEFAULT_LANGUAGE),
            runtime=settings.FUNCTIONS.DEFAULT_RUNTIME,
            methods=settings.FUNCTIONS.DEFAULT_METHODS,
            is_raw=settings.FUNCTIONS.DEFAULT_IS_RAW,
            engine=settings.CONFIG.DEFAULT_CONTAINER_ENGINE,
            cron=settings.FUNCTIONS.DEFAULT_CRON,
            cors=settings.FUNCTIONS.DEFAULT_HAS_CORS,
            timeout=settings.FUNCTIONS.DEFAULT_TIMEOUT_SECONDS,
            created_at=ANY,
            token="",
            verbose=False,
            profile=ANY,
        )

    @patch("cli.functions.commands.executor.create_function")
    def test_dev_add_function_with_custom_options(self, mock_create_function):
        # Action
        custom_name = "CustomFunctionName"
        language = "python"
        runtime = PYTHON_3_9_BASE_RUNTIME
        timeout = 40
        cron_expression = "0 4 * * *"
        result = runner.invoke(
            function_app,
            [
                "dev",
                "add",
                "--name",
                custom_name,
                "--runtime",
                runtime,
                "--language",
                language,
                "--timeout",
                str(timeout),
                "--raw",
                "--cors",
                "--cron",
                cron_expression,
                "--methods",
                "GET",
                "--methods",
                "POST",
                "--verbose",
            ],
        )
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_create_function.assert_called_once_with(
            name=custom_name,
            language=FunctionLanguageEnum(language),
            runtime=runtime,
            methods=[FunctionMethodEnum.GET, FunctionMethodEnum.POST],
            engine=settings.CONFIG.DEFAULT_CONTAINER_ENGINE,
            is_raw=True,
            cron=cron_expression,
            cors=True,
            created_at=ANY,
            token="",
            timeout=timeout,
            verbose=True,
            profile=ANY,
        )

    def test_dev_add_rejects_remote_id_option(self):
        """Verify dev add does not accept --remote-id flag."""
        result = runner.invoke(
            function_app,
            [
                "dev",
                "add",
                "--remote-id",
                "1234",
            ],
        )
        # Should fail because --remote-id is not a valid option
        self.assertNotEqual(result.exit_code, 0)
        # Error message should indicate the option doesn't exist
        output = result.output
        self.assertTrue(
            "--remote-id" in output.lower() or "no such option" in output.lower()
        )


@patch("cli.functions.commands.get_instance_key")
@patch("cli.functions.executor.Pipeline.run")  # Mock the pipeline execution
@patch("typer.confirm", return_value=True)  # Mock user confirmation
class TestDeleteFunctionCommand(TestCase):
    def test_delete_function_by_id(
        self, mock_confirm, mock_pipeline_run, mock_get_instance_key
    ):
        mock_get_instance_key.return_value = "valid_function_key"
        mock_pipeline_run.return_value = None
        result = runner.invoke(function_app, ["delete", "--id", "function123", "--yes"])
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id="function123", label=None)
        mock_pipeline_run.assert_called_once_with(
            {
                "overwrite": {
                    "confirm": True,
                    "message": "Are you sure you want to delete the function?",
                },
                "profile": "",
                "function_key": "valid_function_key",
                "verbose": False,
                "root": "delete_function",
            }
        )

    def test_delete_function_by_label(
        self, mock_confirm, mock_pipeline_run, mock_get_instance_key
    ):
        mock_get_instance_key.return_value = "valid_function_key"
        mock_pipeline_run.return_value = None
        result = runner.invoke(
            function_app, ["delete", "--label", "functionLabel", "--yes"]
        )
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id=None, label="functionLabel")
        mock_pipeline_run.assert_called_once_with(
            {
                "overwrite": {
                    "confirm": True,
                    "message": "Are you sure you want to delete the function?",
                },
                "profile": "",
                "function_key": "valid_function_key",
                "verbose": False,
                "root": "delete_function",
            }
        )

    def test_delete_function_both_id_and_label(
        self, mock_confirm, mock_pipeline_run, mock_get_instance_key
    ):
        mock_get_instance_key.return_value = "valid_function_key"
        mock_pipeline_run.return_value = None
        result = runner.invoke(
            function_app,
            ["delete", "--id", "function123", "--label", "functionLabel", "--yes"],
        )
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(
            id="function123", label="functionLabel"
        )
        mock_pipeline_run.assert_called_once_with(
            {
                "overwrite": {
                    "confirm": True,
                    "message": "Are you sure you want to delete the function?",
                },
                "profile": "",
                "function_key": "valid_function_key",
                "verbose": False,
                "root": "delete_function",
            }
        )


@patch("cli.commons.pipelines.Pipeline.run")
@patch("cli.functions.commands.get_instance_key")
class TestGetFunctionCommand(TestCase):
    def test_get_function_by_id(self, mock_get_instance_key, mock_pipeline_run):
        mock_get_instance_key.return_value = "function_key_from_id"
        mock_pipeline_run.side_effect = lambda _: None  # Ensure no errors

        result = runner.invoke(function_app, ["get", "--id", "function123"])

        self.assertEqual(result.exit_code, 0)

    def test_get_function_with_custom_fields(
        self, mock_get_instance_key, mock_pipeline_run
    ):
        mock_get_instance_key.return_value = "function_key_from_id"
        custom_fields = "runtime,cron"
        mock_pipeline_run.side_effect = lambda _: None  # Ensure no errors

        result = runner.invoke(
            function_app, ["get", "--id", "function123", "--fields", custom_fields]
        )

        self.assertEqual(result.exit_code, 0)

    def test_get_function_both_id_and_label(
        self, mock_get_instance_key, mock_pipeline_run
    ):
        mock_get_instance_key.return_value = "function_key_from_id"
        mock_pipeline_run.side_effect = lambda _: None  # Ensure no errors

        result = runner.invoke(
            function_app, ["get", "--id", "function123", "--label", "functionLabel"]
        )

        self.assertEqual(result.exit_code, 0)


@patch("cli.commons.pipelines.Pipeline.run")
class TestListFunctionsCommand(TestCase):
    def test_list_functions_with_defaults(self, mock_pipeline_run):
        mock_pipeline_run.return_value = None  # Simulate pipeline execution

        result = runner.invoke(function_app, ["list"])

        self.assertEqual(result.exit_code, 0)
        mock_pipeline_run.assert_called_once()

    def test_list_functions_with_custom_options(self, mock_pipeline_run):
        custom_fields = "runtime,raw"
        filter_value = "isActive=true"
        sort_by_value = "created_at"
        page_size_value = 10
        page_value = 2

        mock_pipeline_run.return_value = None  # Simulate pipeline execution

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
        mock_pipeline_run.assert_called_once()


@patch("cli.commons.pipelines.Pipeline.run")
class TestAddFunctionCommand(TestCase):
    def test_add_function_with_minimum_arguments(self, mock_pipeline_run):
        mock_pipeline_run.return_value = None  # Simulate pipeline execution

        result = runner.invoke(function_app, ["add", "TestFunction"])

        self.assertEqual(result.exit_code, 0)
        mock_pipeline_run.assert_called_once_with(
            {
                "profile": "",
                "name": "TestFunction",
                "label": "testfunction",  # Fix: Expect lowercase due to sanitization
                "runtime": DEFAULT_RUNTIME,
                "is_raw": False,
                "http_methods": [
                    FunctionMethodEnum.get_default_method()
                ],  # Fix: Convert to string
                "http_has_cors": False,
                "scheduler_cron": "",
                "timeout": settings.FUNCTIONS.DEFAULT_TIMEOUT_SECONDS,
                "environment": [],  # Fix: Expect a parsed list, not a string
                "root": "add_function",
            }
        )

    def test_add_function_with_all_options(self, mock_pipeline_run):
        mock_pipeline_run.return_value = None  # Simulate pipeline execution

        result = runner.invoke(
            function_app,
            [
                "add",
                "UpdatedFunction",
                "--label",
                "functionLabel",
                "--runtime",
                PYTHON_3_9_BASE_RUNTIME,
                "--raw",
                "--methods",
                "GET",
                "--methods",
                "POST",
                "--cors",
                "--cron",
                "*/5 * * * *",
                "--environment",
                '[{"ENV_VAR": "value"}]',
            ],
        )

        self.assertEqual(result.exit_code, 0)


@patch("cli.commons.pipelines.Pipeline.run")  # Mock pipeline to avoid actual execution
@patch("cli.functions.commands.get_instance_key")
@patch("cli.functions.handlers.update_function")
class TestUpdateFunctionCommand(TestCase):
    def test_update_function_with_minimum_arguments(
        self, mock_update_function, mock_get_instance_key, mock_pipeline_run
    ):
        mock_get_instance_key.return_value = "function_key_from_id"
        mock_pipeline_run.return_value = None  # Simulate pipeline success
        result = runner.invoke(function_app, ["update", "--id", "function123"])
        self.assertEqual(result.exit_code, 0)

    def test_update_function_with_all_options(
        self, mock_update_function, mock_get_instance_key, mock_pipeline_run
    ):
        mock_get_instance_key.return_value = "function_key_from_label"
        mock_pipeline_run.return_value = None  # Simulate pipeline success

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
                PYTHON_3_9_LITE_RUNTIME,
                "--raw",
                "--methods",
                "GET",
                "--methods",
                "POST",
                "--cors",
                "--cron",
                "0 0 * * *",
                "--environment",
                '[{"new_key": "new_value"}]',
            ],
        )
        self.assertEqual(result.exit_code, 0)


@patch("cli.functions.commands.executor.start_function")
class TestDevStartFunctionCommand(TestCase):
    def test_dev_start_function(self, mock_start_function):
        # Action
        result = runner.invoke(function_app, ["dev", "start", "--verbose"])

        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_start_function.assert_called_once_with(verbose=True)


@patch("cli.functions.commands.executor.stop_function")
class TestDevStopFunctionCommand(TestCase):
    def test_dev_stop_function(self, mock_stop_function):
        # Action
        result = runner.invoke(function_app, ["dev", "stop", "--verbose"])

        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_stop_function.assert_called_once_with(verbose=True)


@patch("cli.functions.commands.executor.restart_function")
class TestDevRestartFunctionCommand(TestCase):
    def test_dev_restart_function_with_defaults(self, mock_restart_function):
        # Action
        result = runner.invoke(function_app, ["dev", "restart"])
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_restart_function.assert_called_once_with(
            verbose=False,
        )


@patch("cli.functions.commands.executor.status_function")
class TestDevStatusFunctionCommand(TestCase):
    def test_dev_status_function_with_defaults(self, mock_status_function):
        # Action
        result = runner.invoke(function_app, ["dev", "status"])
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_status_function.assert_called_once_with(
            verbose=False,
        )


@patch("cli.functions.commands.executor.logs_function")
class TestDevLogsCommand(TestCase):
    def test_dev_logs_function_local(self, mock_logs_function):
        """Test dev logs for local container logs only."""
        # Action
        result = runner.invoke(function_app, ["dev", "logs"])

        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_logs_function.assert_called_once_with(
            tail="all",
            follow=False,
            profile="",
            remote=False,  # Always False for dev logs
            verbose=False,
        )

    def test_dev_logs_rejects_remote_flag(self, mock_logs_function):
        """Test that dev logs does not accept --remote flag."""
        # Action
        result = runner.invoke(
            function_app,
            [
                "dev",
                "logs",
                "--remote",
            ],
        )
        # Expected: should fail
        self.assertNotEqual(result.exit_code, 0)


@patch("cli.functions.commands.executor.logs_function")
class TestRootLogsCommand(TestCase):
    def test_root_logs_with_explicit_label(self, mock_logs_function):
        """Test root logs command with explicit function label."""
        # Action
        result = runner.invoke(
            function_app,
            [
                "logs",
                "--label",
                "my-func",
                "--profile",
                "test_profile",
                "--verbose",
            ],
        )

        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_logs_function.assert_called_once_with(
            tail="all",
            follow=False,
            remote=True,
            function_key="~my-func",
            activation_id="",
            last=0,
            profile="test_profile",
            verbose=True,
        )


@patch("cli.functions.commands.executor.push_function")
class TestPushFunctionCommand(TestCase):
    def test_push_function_with_defaults(self, mock_push_function):
        # Action
        result = runner.invoke(function_app, ["push"])
        self.assertEqual(result.exit_code, 0)
        mock_push_function.assert_called_once_with(
            confirm=False,
            profile="",
            verbose=False,
        )

    def test_push_function_with_confirmation(self, mock_push_function):
        # Action
        result = runner.invoke(function_app, ["push", "--yes", "--verbose"])
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_push_function.assert_called_once_with(
            confirm=True,
            profile="",
            verbose=True,
        )


@patch("cli.functions.commands.executor.pull_function")
class TestPullFunctionCommand(TestCase):
    def test_pull_function_with_defaults(self, mock_pull_function):
        # Action
        result = runner.invoke(function_app, ["pull"])
        self.assertEqual(result.exit_code, 0)
        mock_pull_function.assert_called_once_with(
            remote_id="",
            profile="",
            confirm=False,
            verbose=False,
        )

    def test_pull_function_with_confirmation(self, mock_pull_function):
        function_id = "1234"
        # Action
        result = runner.invoke(
            function_app, ["pull", "--yes", "--verbose", "--remote-id", function_id]
        )
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_pull_function.assert_called_once_with(
            remote_id=function_id,
            profile="",
            confirm=True,
            verbose=True,
        )
