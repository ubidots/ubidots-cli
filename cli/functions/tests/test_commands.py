from unittest import TestCase
from unittest.mock import ANY
from unittest.mock import patch

from typer.testing import CliRunner

from cli.functions.commands import app as function_app
from cli.functions.enums import FunctionMethodEnum
from cli.settings import settings

runner = CliRunner()


class TestInitFunctionCommand(TestCase):
    @patch("cli.functions.commands.executor.create_function")
    def test_init_function_with_defaults(self, mock_create_function):
        # Action
        result = runner.invoke(
            function_app,
            [
                "init",
            ],
        )
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_create_function.assert_called_once_with(
            name=settings.FUNCTIONS.DEFAULT_PROJECT_NAME,
            language=settings.FUNCTIONS.DEFAULT_LANGUAGE,
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
        )

    @patch("cli.functions.commands.executor.create_function")
    def test_init_function_with_custom_options(self, mock_create_function):
        # Action
        custom_name = "CustomFunctionName"
        language = "python"
        runtime = "python3.9:base"
        timeout = 40
        cron_expression = "0 4 * * *"
        result = runner.invoke(
            function_app,
            [
                "init",
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
            language=language,
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
        )

    @patch("cli.functions.commands.executor.pull_function")
    def test_init_function_with_remote_id_option(self, mock_pull_function):
        function_id = "1234"
        result = runner.invoke(
            function_app,
            [
                "init",
                "--remote-id",
                function_id,
                "--verbose",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        mock_pull_function.assert_called_once_with(
            remote_id=function_id,
            verbose=True,
        )
