from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock
from unittest.mock import patch

from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.enums import FunctionMethodEnum
from cli.functions.enums import FunctionRuntimeLayerTypeEnum
from cli.functions.executor import clean_functions
from cli.functions.executor import create_function
from cli.functions.executor import logs_function
from cli.functions.executor import pull_function
from cli.functions.executor import push_function
from cli.functions.executor import restart_function
from cli.functions.executor import start_function
from cli.functions.executor import status_function
from cli.functions.executor import stop_function
from cli.settings import settings


class TestCreateFunction(TestCase):
    @patch("cli.functions.executor.Pipeline")
    @patch("cli.functions.pipelines.ValidateTemplateStep")
    @patch("cli.functions.pipelines.CreateProjectFolderStep")
    @patch("cli.functions.pipelines.ExtractTemplateStep")
    @patch("cli.functions.pipelines.SaveManifestStep")
    def test_create_function(
        self,
        MockSaveManifestStep,
        MockExtractStep,
        MockCreateFolderStep,
        MockValidateStep,
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
        # Action
        create_function(
            name=name,
            language=language,
            runtime=runtime,
            methods=methods,
            is_raw=is_raw,
            cron=cron,
            cors=cors,
            verbose=verbose,
        )
        # Expected
        MockPipeline.assert_called_once_with(
            [
                MockValidateStep.return_value,
                MockCreateFolderStep.return_value,
                MockExtractStep.return_value,
                MockSaveManifestStep.return_value,
            ],
            success_message=f"Project '{name}' created in '{Path.cwd() / name}'.",
        )
        mock_pipeline_instance.run.assert_called_once_with(
            {
                "project_path": Path.cwd() / name,
                "template_file": settings.FUNCTIONS.TEMPLATES_PATH / f"{language}.zip",
                "language": language,
                "runtime": runtime,
                "is_raw": is_raw,
                "methods": methods,
                "has_cors": cors,
                "cron": cron,
                "verbose": verbose,
                "root": create_function.__name__,
            }
        )


class TestStartFunction(TestCase):
    @patch("cli.functions.executor.Pipeline")
    @patch("cli.functions.pipelines.ReadManifestStep")
    @patch("cli.functions.pipelines.GetProjectFilesStep")
    @patch("cli.functions.pipelines.ValidateProjectStep")
    @patch("cli.functions.pipelines.GetClientStep")
    @patch("cli.functions.pipelines.GetImageNamesStep")
    @patch("cli.functions.pipelines.ValidateImageNamesStep")
    @patch("cli.functions.pipelines.ShowStartupInfoStep")
    @patch("cli.functions.pipelines.GetContainerManagerStep")
    @patch("cli.functions.pipelines.GetClientNetworkStep")
    @patch("cli.functions.pipelines.GetArgoContainerManagerStep")
    @patch("cli.functions.pipelines.GetArgoContainerInputAdapterStep")
    @patch("cli.functions.pipelines.CreateArgoContainerAdapterStep")
    @patch("cli.functions.pipelines.CreateHandlerFRIEStep")
    @patch("cli.functions.pipelines.GetFRIEContainerTargetStep")
    @patch("cli.functions.pipelines.SaveManifestStep")
    @patch("cli.functions.pipelines.PrintkeyStep")
    def test_start_function(
        self,
        MockPrintkeyStep,
        MockSaveManifestStep,
        MockGetFRIEContainerTargetStep,
        MockCreateHandlerFRIEStep,
        MockCreateArgoContainerAdapterStep,
        MockGetArgoContainerInputAdapterStep,
        MockGetArgoContainerManagerStep,
        MockGetClientNetworkStep,
        MockGetContainerManagerStep,
        MockShowStartupInfoStep,
        MockValidateImageNamesStep,
        MockGetImageNamesStep,
        MockGetClientStep,
        MockValidateProjectStep,
        MockGetProjectFilesStep,
        MockReadManifestStep,
        MockPipeline,
    ):
        # Setup
        mock_pipeline_instance = MockPipeline.return_value
        mock_pipeline_instance.run = MagicMock()

        engine = FunctionEngineTypeEnum.DOCKER
        methods = [FunctionMethodEnum.GET, FunctionMethodEnum.POST]
        is_raw = True
        token = "test_token"
        cors = True
        cron = "* * * * *"
        timeout = 60
        verbose = True
        # Action
        start_function(
            engine=engine,
            methods=methods,
            is_raw=is_raw,
            token=token,
            cors=cors,
            cron=cron,
            timeout=timeout,
            verbose=verbose,
        )
        # Expected
        MockPipeline.assert_called_once_with(
            [
                MockReadManifestStep.return_value,
                MockGetProjectFilesStep.return_value,
                MockValidateProjectStep.return_value,
                MockGetClientStep.return_value,
                MockGetImageNamesStep.return_value,
                MockValidateImageNamesStep.return_value,
                MockShowStartupInfoStep.return_value,
                MockGetContainerManagerStep.return_value,
                MockGetClientNetworkStep.return_value,
                MockGetArgoContainerManagerStep.return_value,
                MockGetArgoContainerInputAdapterStep.return_value,
                MockCreateArgoContainerAdapterStep.return_value,
                MockCreateHandlerFRIEStep.return_value,
                MockGetFRIEContainerTargetStep.return_value,
                MockSaveManifestStep.return_value,
                MockPrintkeyStep.return_value,
            ],
            success_message="Function started successfully.",
        )
        mock_pipeline_instance.run.assert_called_once_with(
            {
                "project_path": Path.cwd(),
                "validations": {
                    "manifest_file_exists": True,
                    "function_exists": False,
                },
                "is_raw": is_raw,
                "methods": methods,
                "has_cors": cors,
                "token": token,
                "cron": cron,
                "timeout": timeout,
                "verbose": verbose,
                "root": start_function.__name__,
            }
        )


class TestStopFunction(TestCase):
    @patch("cli.functions.executor.Pipeline")
    @patch("cli.functions.pipelines.GetClientStep")
    @patch("cli.functions.pipelines.GetContainerManagerStep")
    @patch("cli.functions.pipelines.ReadManifestStep")
    @patch("cli.functions.pipelines.GetContainerKeyStep")
    @patch("cli.functions.pipelines.RemoveNonDeployableFilesStep")
    @patch("cli.functions.pipelines.StopFunctionStep")
    @patch("cli.functions.pipelines.PrintkeyStep")
    def test_stop_function(
        self,
        MockPrintkeyStep,
        MockStopFunctionStep,
        MockRemoveNonDeployableFilesStep,
        MockGetContainerKeyStep,
        MockReadManifestStep,
        MockGetContainerManagerStep,
        MockGetClientStep,
        MockPipeline,
    ):
        # Setup
        mock_pipeline_instance = MockPipeline.return_value
        mock_pipeline_instance.run = MagicMock()

        engine = FunctionEngineTypeEnum.DOCKER
        label = "test_label"
        verbose = True
        # Action
        stop_function(engine=engine, label=label, verbose=verbose)
        # Expected
        MockPipeline.assert_called_once_with(
            [
                MockGetClientStep.return_value,
                MockGetContainerManagerStep.return_value,
                MockReadManifestStep.return_value,
                MockGetContainerKeyStep.return_value,
                MockRemoveNonDeployableFilesStep.return_value,
                MockStopFunctionStep.return_value,
                MockPrintkeyStep.return_value,
            ],
            success_message="Function stoped successfully.",
        )
        mock_pipeline_instance.run.assert_called_once_with(
            {
                "project_path": Path.cwd(),
                "container_key": label,
                "verbose": verbose,
                "root": stop_function.__name__,
            }
        )


class TestRestartFunction(TestCase):
    @patch("cli.functions.executor.Pipeline")
    @patch("cli.functions.pipelines.GetClientStep")
    @patch("cli.functions.pipelines.GetContainerManagerStep")
    @patch("cli.functions.pipelines.ReadManifestStep")
    @patch("cli.functions.pipelines.GetContainerKeyStep")
    @patch("cli.functions.pipelines.RestartFunctionStep")
    def test_restart_function(
        self,
        MockRestartFunctionStep,
        MockGetContainerKeyStep,
        MockReadManifestStep,
        MockGetContainerManagerStep,
        MockGetClientStep,
        MockPipeline,
    ):
        # Setup
        mock_pipeline_instance = MockPipeline.return_value
        mock_pipeline_instance.run = MagicMock()

        engine = FunctionEngineTypeEnum.DOCKER
        verbose = True
        # Action
        restart_function(engine=engine, verbose=verbose)
        # Expected
        MockPipeline.assert_called_once_with(
            [
                MockGetClientStep.return_value,
                MockGetContainerManagerStep.return_value,
                MockReadManifestStep.return_value,
                MockGetContainerKeyStep.return_value,
                MockRestartFunctionStep.return_value,
            ],
            success_message="Function restarted successfully.",
        )
        mock_pipeline_instance.run.assert_called_once_with(
            {
                "project_path": Path.cwd(),
                "verbose": verbose,
                "root": restart_function.__name__,
            }
        )


class TestStatusFunction(TestCase):
    @patch("cli.functions.executor.Pipeline")
    @patch("cli.functions.pipelines.GetClientStep")
    @patch("cli.functions.pipelines.GetContainerManagerStep")
    @patch("cli.functions.pipelines.GetFunctionStatusStep")
    @patch("cli.functions.pipelines.PrintColoredTableStep")
    def test_status_function(
        self,
        MockPrintColoredTableStep,
        MockGetFunctionStatusStep,
        MockGetContainerManagerStep,
        MockGetClientStep,
        MockPipeline,
    ):
        # Setup
        mock_pipeline_instance = MockPipeline.return_value
        mock_pipeline_instance.run = MagicMock()

        engine = FunctionEngineTypeEnum.DOCKER
        verbose = True
        # Action
        status_function(engine=engine, verbose=verbose)
        # Expected
        MockPipeline.assert_called_once_with(
            [
                MockGetClientStep.return_value,
                MockGetContainerManagerStep.return_value,
                MockGetFunctionStatusStep.return_value,
                MockPrintColoredTableStep.return_value,
            ]
        )
        mock_pipeline_instance.run.assert_called_once_with(
            {
                "verbose": verbose,
                "root": status_function.__name__,
            }
        )


class TestLogsFunction(TestCase):
    @patch("cli.functions.executor.Pipeline")
    @patch("cli.functions.pipelines.ReadManifestStep")
    @patch("cli.functions.pipelines.GetProjectFilesStep")
    @patch("cli.functions.pipelines.ValidateProjectStep")
    @patch("cli.functions.pipelines.BuildEndpointStep")
    @patch("cli.functions.pipelines.HttpGetRequestStep")
    @patch("cli.functions.pipelines.CheckResponseStep")
    @patch("cli.functions.pipelines.PrintColoredTableStep")
    def test_logs_function_remote(
        self,
        MockPrintColoredTableStep,
        MockCheckResponseStep,
        MockHttpGetRequestStep,
        MockBuildEndpointStep,
        MockValidateProjectStep,
        MockGetProjectFilesStep,
        MockReadManifestStep,
        MockPipeline,
    ):
        # Setup
        mock_pipeline_instance = MockPipeline.return_value
        mock_pipeline_instance.run = MagicMock()

        engine = FunctionEngineTypeEnum.DOCKER
        label = "test_label"
        tail = "10"
        follow = True
        remote = True
        verbose = True
        # Action
        logs_function(
            engine=engine,
            label=label,
            tail=tail,
            follow=follow,
            remote=remote,
            verbose=verbose,
        )
        # Expected
        MockPipeline.assert_called_once_with(
            [
                MockReadManifestStep.return_value,
                MockGetProjectFilesStep.return_value,
                MockValidateProjectStep.return_value,
                MockBuildEndpointStep.return_value,
                MockHttpGetRequestStep.return_value,
                MockCheckResponseStep.return_value,
                MockPrintColoredTableStep.return_value,
            ]
        )
        mock_pipeline_instance.run.assert_called_once_with(
            {
                "project_path": Path.cwd(),
                "validations": {
                    "manifest_file_exists": True,
                    "function_exists": True,
                },
                "verbose": verbose,
                "root": logs_function.__name__,
            }
        )

    @patch("cli.functions.executor.Pipeline")
    @patch("cli.functions.pipelines.GetClientStep")
    @patch("cli.functions.pipelines.GetContainerManagerStep")
    @patch("cli.functions.pipelines.GetFunctionLogsStep")
    @patch("cli.functions.pipelines.PrintkeyStep")
    def test_logs_function_local(
        self,
        MockPrintkeyStep,
        MockGetFunctionLogsStep,
        MockGetContainerManagerStep,
        MockGetClientStep,
        MockPipeline,
    ):
        # Setup
        mock_pipeline_instance = MockPipeline.return_value
        mock_pipeline_instance.run = MagicMock()

        engine = FunctionEngineTypeEnum.DOCKER
        label = "test_label"
        tail = "10"
        follow = True
        remote = False
        verbose = True
        # Action
        logs_function(
            engine=engine,
            label=label,
            tail=tail,
            follow=follow,
            remote=remote,
            verbose=verbose,
        )
        # Expected
        MockPipeline.assert_called_once_with(
            [
                MockGetClientStep.return_value,
                MockGetContainerManagerStep.return_value,
                MockGetFunctionLogsStep.return_value,
                MockPrintkeyStep.return_value,
            ]
        )
        mock_pipeline_instance.run.assert_called_once_with(
            {
                "container_key": label,
                "verbose": verbose,
                "root": logs_function.__name__,
            }
        )


class TestPushFunction(TestCase):
    @patch("cli.functions.executor.Pipeline")
    @patch("cli.functions.pipelines.ReadManifestStep")
    @patch("cli.functions.pipelines.GetProjectFilesStep")
    @patch("cli.functions.pipelines.ValidateProjectStep")
    @patch("cli.functions.pipelines.ConfirmOverwriteStep")
    @patch("cli.functions.pipelines.BuildEndpointStep")
    @patch("cli.functions.pipelines.CreateFunctionStep")
    @patch("cli.functions.pipelines.SaveManifestStep")
    @patch("cli.functions.pipelines.UpdateFunctionStep")
    @patch("cli.functions.pipelines.CompressProjectStep")
    @patch("cli.functions.pipelines.UploadFileStep")
    @patch("cli.functions.pipelines.CheckResponseStep")
    def test_push_function(
        self,
        MockCheckResponseStep,
        MockUploadFileStep,
        MockCompressProjectStep,
        MockUpdateFunctionStep,
        MockSaveManifestStep,
        MockCreateFunctionStep,
        MockBuildEndpointStep,
        MockConfirmOverwriteStep,
        MockValidateProjectStep,
        MockGetProjectFilesStep,
        MockReadManifestStep,
        MockPipeline,
    ):
        # Setup
        mock_pipeline_instance = MockPipeline.return_value
        mock_pipeline_instance.run = MagicMock()

        confirm = True
        verbose = True
        # Action
        push_function(confirm=confirm, verbose=verbose)
        # Expected
        MockPipeline.assert_called_once_with(
            [
                MockReadManifestStep.return_value,
                MockGetProjectFilesStep.return_value,
                MockValidateProjectStep.return_value,
                MockConfirmOverwriteStep.return_value,
                MockBuildEndpointStep.return_value,
                MockCreateFunctionStep.return_value,
                MockSaveManifestStep.return_value,
                MockBuildEndpointStep.return_value,
                MockUpdateFunctionStep.return_value,
                MockReadManifestStep.return_value,
                MockCompressProjectStep.return_value,
                MockBuildEndpointStep.return_value,
                MockUploadFileStep.return_value,
                MockCheckResponseStep.return_value,
            ],
            success_message="Function uploaded successfully.",
        )
        mock_pipeline_instance.run.assert_called_once_with(
            {
                "project_path": Path.cwd(),
                "overwrite": {
                    "confirm": confirm,
                    "message": "Are you sure you want to overwrite the remote files?",
                },
                "validations": {
                    "manifest_file_exists": True,
                    "function_exists": True,
                },
                "verbose": verbose,
                "root": push_function.__name__,
            }
        )


class TestPullFunction(TestCase):
    @patch("cli.functions.executor.Pipeline")
    @patch("cli.functions.pipelines.ReadManifestStep")
    @patch("cli.functions.pipelines.GetProjectFilesStep")
    @patch("cli.functions.pipelines.ValidateProjectStep")
    @patch("cli.functions.pipelines.ConfirmOverwriteStep")
    @patch("cli.functions.pipelines.BuildEndpointStep")
    @patch("cli.functions.pipelines.DownloadFileStep")
    @patch("cli.functions.pipelines.CheckResponseStep")
    @patch("cli.functions.pipelines.ExtractProjectStep")
    def test_pull_function(
        self,
        MockExtractProjectStep,
        MockCheckResponseStep,
        MockDownloadFileStep,
        MockBuildEndpointStep,
        MockConfirmOverwriteStep,
        MockValidateProjectStep,
        MockGetProjectFilesStep,
        MockReadManifestStep,
        MockPipeline,
    ):
        # Setup
        mock_pipeline_instance = MockPipeline.return_value
        mock_pipeline_instance.run = MagicMock()

        confirm = True
        verbose = True
        # Action
        pull_function(confirm=confirm, verbose=verbose)
        # Expected
        MockPipeline.assert_called_once_with(
            [
                MockReadManifestStep.return_value,
                MockGetProjectFilesStep.return_value,
                MockValidateProjectStep.return_value,
                MockConfirmOverwriteStep.return_value,
                MockBuildEndpointStep.return_value,
                MockDownloadFileStep.return_value,
                MockCheckResponseStep.return_value,
                MockExtractProjectStep.return_value,
            ],
            success_message="Function downloaded successfully.",
        )
        mock_pipeline_instance.run.assert_called_once_with(
            {
                "project_path": Path.cwd(),
                "overwrite": {
                    "confirm": confirm,
                    "message": "Are you sure you want to overwrite the local files?",
                },
                "validations": {
                    "manifest_file_exists": True,
                    "function_exists": True,
                },
                "verbose": verbose,
                "root": pull_function.__name__,
            }
        )


class TestCleanFunctions(TestCase):
    @patch("cli.functions.executor.Pipeline")
    @patch("cli.functions.pipelines.ConfirmOverwriteStep")
    @patch("cli.functions.pipelines.GetClientStep")
    @patch("cli.functions.pipelines.GetContainerManagerStep")
    @patch("cli.functions.pipelines.CleanFunctionsStep")
    def test_clean_functions(
        self,
        MockCleanFunctionsStep,
        MockGetContainerManagerStep,
        MockGetClientStep,
        MockConfirmOverwriteStep,
        MockPipeline,
    ):
        # Setup
        mock_pipeline_instance = MockPipeline.return_value
        mock_pipeline_instance.run = MagicMock()

        engine = FunctionEngineTypeEnum.DOCKER
        confirm = True
        verbose = True
        # Action
        clean_functions(engine=engine, confirm=confirm, verbose=verbose)
        # Expected
        MockPipeline.assert_called_once_with(
            [
                MockConfirmOverwriteStep.return_value,
                MockGetClientStep.return_value,
                MockGetContainerManagerStep.return_value,
                MockCleanFunctionsStep.return_value,
            ]
        )
        mock_pipeline_instance.run.assert_called_once_with(
            {
                "overwrite": {
                    "confirm": confirm,
                    "message": (
                        "Are you sure you want to proceed?\n"
                        "This will remove all unused images, containers, and networks, which cannot be undone."
                    ),
                },
                "verbose": verbose,
                "root": clean_functions.__name__,
            }
        )
