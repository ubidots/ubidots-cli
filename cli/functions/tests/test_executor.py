from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock
from unittest.mock import patch

from cli.functions.enums import FunctionLanguageEnum
from cli.functions.enums import FunctionMethodEnum
from cli.functions.enums import FunctionRuntimeLayerTypeEnum
from cli.functions.executor import create_function
from cli.settings import settings


class TestCreateFunction(TestCase):
    @patch("cli.functions.executor.Pipeline")
    @patch("cli.functions.pipelines.ValidateAllowedRuntimeStep")
    @patch("cli.functions.pipelines.ValidateRuntimeAgaisntLanguageStep")
    @patch("cli.functions.pipelines.ValidateTemplateStep")
    @patch("cli.functions.pipelines.CreateProjectFolderStep")
    @patch("cli.functions.pipelines.ExtractTemplateStep")
    @patch("cli.functions.pipelines.SaveManifestStep")
    def test_create_function(
        self,
        MockSaveManifestStep,
        MockExtractTemplateStep,
        MockCreateFolderStep,
        MockValidateTemplateStep,
        MockValidateRuntimeAgaisntLanguageStep,
        MockValidateAllowedRuntimeStep,
        MockPipeline,
    ):
        # Setup
        settings.FUNCTIONS.TEMPLATES_PATH = Path("/fake/templates/path")
        mock_pipeline_instance = MockPipeline.return_value
        mock_pipeline_instance.run = MagicMock()

        name = "default_function"
        language = FunctionLanguageEnum.PYTHON
        runtime = FunctionRuntimeLayerTypeEnum.PYTHON_3_9_BASE
        methods = [FunctionMethodEnum.GET, FunctionMethodEnum.POST]
        is_raw = False
        cron = ""
        cors = False
        verbose = False
        engine = settings.CONFIG.DEFAULT_CONTAINER_ENGINE
        timeout = settings.FUNCTIONS.DEFAULT_TIMEOUT_SECONDS
        fixed_created_at = "2025-02-18T15:00:00"
        # Action: call create_function with the new required parameters.
        create_function(
            name=name,
            language=language,
            runtime=runtime,
            methods=methods,
            is_raw=is_raw,
            engine=engine,
            cron=cron,
            cors=cors,
            verbose=verbose,
            timeout=timeout,
            created_at=fixed_created_at,
        )

        expected_steps = [
            MockValidateAllowedRuntimeStep.return_value,
            MockValidateRuntimeAgaisntLanguageStep.return_value,
            MockValidateTemplateStep.return_value,
            MockCreateFolderStep.return_value,
            MockExtractTemplateStep.return_value,
            MockSaveManifestStep.return_value,
        ]
        MockPipeline.assert_called_once_with(
            expected_steps,
            success_message=f"Project '{name}' created in '{Path.cwd() / name}'.",
        )
        expected_context = {
            "project_path": Path.cwd() / name,
            "name": name,
            "label": name,
            "template_file": settings.FUNCTIONS.TEMPLATES_PATH
            / f"{language.value}.zip",
            "language": language,
            "runtime": runtime,
            "methods": methods,
            "is_raw": is_raw,
            "cron": cron,
            "has_cron": False,
            "has_cors": cors,
            "verbose": verbose,
            "root": create_function.__name__,
            "engine": engine,
            "timeout": timeout,
            "created_at": fixed_created_at,
            "token": "",
            "function_id": "",
            "params": {},
            "http_enabled": settings.FUNCTIONS.DEFAULT_HTTP_ENABLED,
            "http_has_cors": False,
            "http_is_secure": False,
        }
        mock_pipeline_instance.run.assert_called_once_with(expected_context)
