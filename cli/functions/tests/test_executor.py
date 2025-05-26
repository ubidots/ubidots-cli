from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock
from unittest.mock import patch

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
    @patch("cli.functions.pipelines.ValidateNotInExistingFunctionDirectoryStep")
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
        MockValidateNotInExistingFunctionDirectoryStep,
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
        profile = ""

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
            profile=profile,
        )

        expected_steps = [
            MockValidateNotInExistingFunctionDirectoryStep.return_value,
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
            "http_enabled": settings.FUNCTIONS.DEFAULT_HTTP_ENABLED,
            "http_has_cors": False,
            "http_is_secure": False,
            "profile": profile,
            "params": "{}",
        }
        mock_pipeline_instance.run.assert_called_once_with(expected_context)

    @patch("cli.functions.executor.Pipeline")
    @patch("cli.functions.pipelines.ValidateNotInExistingFunctionDirectoryStep")
    def test_create_function_fails_in_existing_directory(
        self,
        MockValidateNotInExistingFunctionDirectoryStep,
        MockPipeline,
    ):
        # Setup: Mock the validation step to raise an error
        MockValidateNotInExistingFunctionDirectoryStep.side_effect = ValueError(
            "Error: Cannot run 'functions init' from within an existing "
            "function directory. Please navigate to a different directory "
            "to create a new function."
        )

        mock_pipeline_instance = MockPipeline.return_value
        mock_pipeline_instance.run = MagicMock()

        # Action & Assert: Expect ValueError when in existing function directory
        with self.assertRaises(ValueError) as context:
            create_function(
                name="test_function",
                language=FunctionLanguageEnum.PYTHON,
                runtime=FunctionRuntimeLayerTypeEnum.PYTHON_3_9_BASE,
                methods=[FunctionMethodEnum.GET],
                is_raw=False,
                engine=settings.CONFIG.DEFAULT_CONTAINER_ENGINE,
                cron="",
                cors=False,
                verbose=False,
                timeout=settings.FUNCTIONS.DEFAULT_TIMEOUT_SECONDS,
                created_at="2025-02-18T15:00:00",
                profile="",
            )

        self.assertIn("Cannot run 'functions init'", str(context.exception))


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
        verbose = True

        # Action
        start_function(verbose=verbose)

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
                MockPrintkeyStep.return_value,
            ],
            success_message="Function started successfully.",
        )
        mock_pipeline_instance.run.assert_called_once_with(
            {
                "project_path": Path.cwd(),
                "validations": {
                    "manifest_file": True,
                    "function_exists": False,
                },
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
        verbose = True

        # Action
        stop_function(verbose=verbose)

        # Expected
        MockPipeline.assert_called_once_with(
            [
                MockReadManifestStep.return_value,  # FIX: First in list
                MockGetClientStep.return_value,
                MockGetContainerManagerStep.return_value,
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
        verbose = True

        # Action
        restart_function(verbose=verbose)

        # Expected
        MockPipeline.assert_called_once_with(
            [
                MockReadManifestStep.return_value,  # FIX: First in list
                MockGetClientStep.return_value,
                MockGetContainerManagerStep.return_value,
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
    @patch("cli.functions.pipelines.ReadManifestStep")
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
        MockReadManifestStep,
        MockPipeline,
    ):
        # Setup
        mock_pipeline_instance = MockPipeline.return_value
        mock_pipeline_instance.run = MagicMock()
        verbose = True

        # Action
        status_function(verbose=verbose)

        # Expected
        MockPipeline.assert_called_once_with(
            [
                MockReadManifestStep.return_value,
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
                "project_path": Path.cwd(),
            }
        )


class TestLogsFunction(TestCase):
    @patch("cli.functions.executor.Pipeline")
    @patch("cli.functions.pipelines.ReadManifestStep")
    @patch("cli.functions.pipelines.GetProjectFilesStep")
    @patch("cli.functions.pipelines.ValidateProjectStep")
    @patch("cli.functions.pipelines.GetFunctionIdFromManifestStep")
    @patch("cli.functions.pipelines.GetActiveConfigStep")
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
        MockGetActiveConfigStep,
        MockGetFunctionIdFromManifestStep,
        MockValidateProjectStep,
        MockGetProjectFilesStep,
        MockReadManifestStep,
        MockPipeline,
    ):
        # Setup
        mock_pipeline_instance = MockPipeline.return_value
        mock_pipeline_instance.run = MagicMock()
        tail = "10"
        follow = True
        remote = True
        profile = "test_profile"
        verbose = True

        # Action
        logs_function(
            tail=tail,
            follow=follow,
            profile=profile,
            remote=remote,
            verbose=verbose,
        )

        # Expected
        MockPipeline.assert_called_once_with(
            [
                MockReadManifestStep.return_value,
                MockGetProjectFilesStep.return_value,
                MockValidateProjectStep.return_value,
                MockGetFunctionIdFromManifestStep.return_value,
                MockGetActiveConfigStep.return_value,
                MockBuildEndpointStep.return_value,
                MockHttpGetRequestStep.return_value,
                MockCheckResponseStep.return_value,
                MockPrintColoredTableStep.return_value,
            ]
        )
        mock_pipeline_instance.run.assert_called_once_with(
            {
                "project_path": Path.cwd(),
                "profile": profile,
                "validations": {
                    "manifest_file_exists": True,
                    "function_exists": True,
                },
                "verbose": verbose,
                "root": logs_function.__name__,
            }
        )

    @patch("cli.functions.executor.Pipeline")
    @patch("cli.functions.pipelines.ReadManifestStep")
    @patch("cli.functions.pipelines.GetClientStep")
    @patch("cli.functions.pipelines.GetContainerManagerStep")
    @patch("cli.functions.pipelines.GetContainerKeyStep")
    @patch("cli.functions.pipelines.GetFunctionLogsStep")
    @patch("cli.functions.pipelines.PrintkeyStep")
    def test_logs_function_local(
        self,
        MockPrintkeyStep,
        MockGetFunctionLogsStep,
        MockGetContainerKeyStep,
        MockGetContainerManagerStep,
        MockGetClientStep,
        MockReadManifestStep,
        MockPipeline,
    ):
        # Setup
        mock_pipeline_instance = MockPipeline.return_value
        mock_pipeline_instance.run = MagicMock()
        tail = "10"
        follow = True
        remote = False
        verbose = True

        # Action
        logs_function(
            tail=tail,
            follow=follow,
            profile="",  # No profile needed for local
            remote=remote,
            verbose=verbose,
        )

        # Expected
        MockPipeline.assert_called_once_with(
            [
                MockReadManifestStep.return_value,
                MockGetClientStep.return_value,
                MockGetContainerManagerStep.return_value,
                MockGetContainerKeyStep.return_value,
                MockGetFunctionLogsStep.return_value,
                MockPrintkeyStep.return_value,
            ]
        )
        mock_pipeline_instance.run.assert_called_once_with(
            {
                "verbose": verbose,
                "root": logs_function.__name__,
                "project_path": Path.cwd(),
            }
        )


class TestPushFunction(TestCase):
    @patch("cli.functions.executor.Pipeline")
    @patch("cli.functions.pipelines.GetActiveConfigStep")
    @patch("cli.functions.pipelines.ReadManifestStep")
    @patch("cli.functions.pipelines.GetProjectFilesStep")
    @patch("cli.functions.pipelines.ValidateProjectStep")
    @patch("cli.functions.pipelines.ValidateRemoteFunctionExistStep")
    @patch("cli.functions.pipelines.BuildEndpointStep")
    @patch("cli.functions.pipelines.CreateFunctionStep")
    @patch("cli.functions.pipelines.SaveFunctionIDStep")
    @patch("cli.functions.pipelines.ConfirmOverwritePushFunctionStep")
    @patch("cli.functions.pipelines.UpdateFunctionSettings")
    @patch("cli.functions.pipelines.CompressProjectStep")
    @patch("cli.functions.pipelines.UploadFileStep")
    @patch("cli.functions.pipelines.CheckResponseStep")
    def test_push_function(
        self,
        MockCheckResponseStep,
        MockUploadFileStep,
        MockCompressProjectStep,
        MockUpdateFunctionSettings,
        MockConfirmOverwritePushFunctionStep,
        MockSaveFunctionIDStep,
        MockCreateFunctionStep,
        MockBuildEndpointStep,
        MockValidateRemoteFunctionExistStep,
        MockValidateProjectStep,
        MockGetProjectFilesStep,
        MockReadManifestStep,
        MockGetActiveConfigStep,
        MockPipeline,
    ):
        # Setup
        mock_pipeline_instance = MockPipeline.return_value
        mock_pipeline_instance.run = MagicMock()
        confirm = True
        verbose = True
        profile = "test_profile"

        # Action
        push_function(confirm=confirm, profile=profile, verbose=verbose)

        # Expected
        MockPipeline.assert_called_once_with(
            [
                MockGetActiveConfigStep.return_value,
                MockReadManifestStep.return_value,
                MockGetProjectFilesStep.return_value,
                MockValidateProjectStep.return_value,
                MockValidateRemoteFunctionExistStep.return_value,
                MockBuildEndpointStep.return_value,  # base URL
                MockCreateFunctionStep.return_value,
                MockSaveFunctionIDStep.return_value,
                MockConfirmOverwritePushFunctionStep.return_value,
                MockBuildEndpointStep.return_value,  # detail URL
                MockUpdateFunctionSettings.return_value,
                MockBuildEndpointStep.return_value,  # zip file URL
                MockCompressProjectStep.return_value,
                MockUploadFileStep.return_value,
                MockCheckResponseStep.return_value,
            ],
            success_message="Function uploaded successfully.",
        )

        mock_pipeline_instance.run.assert_called_once_with(
            {
                "project_path": Path.cwd(),
                "profile": profile,
                "overwrite": {
                    "confirm": confirm,
                    "message": "Are you sure you want to overwrite the remote files?",
                },
                "validations": {
                    "manifest_file": True,
                    "function_exists": False,
                },
                "verbose": verbose,
                "root": push_function.__name__,
            }
        )


class TestPullFunction(TestCase):
    @patch("cli.functions.executor.Pipeline")
    @patch("cli.functions.pipelines.GetActiveConfigStep")
    @patch("cli.functions.pipelines.CheckRemoteIdRequirementStep")
    @patch("cli.functions.pipelines.GetRemoteFunctionDetailSteps")
    @patch("cli.functions.pipelines.CheckFunctionDetailResponse")
    @patch("cli.functions.pipelines.ParseFunctionDetailsResponse")
    @patch("cli.functions.pipelines.GetRemoteFunctionLocalMetadataStep")
    @patch("cli.functions.pipelines.ValidateFunctionHasAlreadyBeenPulled")
    @patch("cli.functions.pipelines.ConfirmOverwritePullFunctionStep")
    @patch("cli.functions.pipelines.BuildEndpointStep")
    @patch("cli.functions.pipelines.DownloadFileStep")
    @patch("cli.functions.pipelines.CheckResponseStep")
    @patch("cli.functions.pipelines.ExtractProjectStep")
    @patch("cli.functions.pipelines.GetFunctionParametersStep")
    @patch("cli.functions.pipelines.SaveManifestStep")
    @patch("cli.functions.pipelines.ReadManifestStep")
    @patch("cli.functions.pipelines.GetProjectFilesStep")
    @patch("cli.functions.pipelines.ValidateProjectStep")
    @patch("cli.functions.pipelines.PrintFunctionPath")
    def test_pull_function(
        self,
        MockPrintFunctionPath,
        MockValidateProjectStep,
        MockGetProjectFilesStep,
        MockReadManifestStep,
        MockSaveManifestStep,
        MockGetFunctionParametersStep,
        MockExtractProjectStep,
        MockCheckResponseStep,
        MockDownloadFileStep,
        MockBuildEndpointStep,
        MockConfirmOverwritePullFunctionStep,
        MockValidateFunctionHasAlreadyBeenPulled,
        MockGetRemoteFunctionLocalMetadataStep,
        MockParseFunctionDetailsResponse,
        MockCheckFunctionDetailResponse,
        MockGetRemoteFunctionDetailSteps,
        MockCheckRemoteIdRequirementStep,
        MockGetActiveConfigStep,
        MockPipeline,
    ):
        # Setup
        mock_pipeline_instance = MockPipeline.return_value
        mock_pipeline_instance.run = MagicMock()
        confirm = True
        verbose = True
        profile = "test_profile"
        remote_id = "test_function_123"

        # Action
        pull_function(
            remote_id=remote_id, profile=profile, confirm=confirm, verbose=verbose
        )

        # Expected
        MockPipeline.assert_called_once_with(
            [
                MockGetActiveConfigStep.return_value,
                MockCheckRemoteIdRequirementStep.return_value,
                MockGetRemoteFunctionDetailSteps.return_value,
                MockCheckFunctionDetailResponse.return_value,
                MockParseFunctionDetailsResponse.return_value,
                MockGetRemoteFunctionLocalMetadataStep.return_value,
                MockValidateFunctionHasAlreadyBeenPulled.return_value,
                MockConfirmOverwritePullFunctionStep.return_value,
                MockBuildEndpointStep.return_value,
                MockDownloadFileStep.return_value,
                MockCheckResponseStep.return_value,
                MockExtractProjectStep.return_value,
                MockGetFunctionParametersStep.return_value,
                MockSaveManifestStep.return_value,
                MockReadManifestStep.return_value,
                MockGetProjectFilesStep.return_value,
                MockValidateProjectStep.return_value,
                MockPrintFunctionPath.return_value,
            ]
        )

        mock_pipeline_instance.run.assert_called_once_with(
            {
                "project_path": Path.cwd(),
                "confirm": confirm,
                "profile": profile,
                "remote_id": remote_id,
                "verbose": verbose,
                "root": pull_function.__name__,
                "validations": {
                    "manifest_file_exists": True,
                    "function_exists": True,
                },
            }
        )


class TestCleanFunctions(TestCase):
    @patch("cli.functions.executor.Pipeline")
    @patch("cli.functions.pipelines.ReadManifestStep")
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
        MockReadManifestStep,
        MockPipeline,
    ):
        # Setup
        mock_pipeline_instance = MockPipeline.return_value
        mock_pipeline_instance.run = MagicMock()
        confirm = True
        verbose = True

        # Action
        clean_functions(confirm=confirm, verbose=verbose)

        # Expected
        MockPipeline.assert_called_once_with(
            [
                MockReadManifestStep.return_value,
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
                "project_path": Path.cwd(),
                "verbose": verbose,
                "root": clean_functions.__name__,
            }
        )
