import zipfile

import pytest
import yaml
from typer.testing import CliRunner

from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.enums import FunctionRuntimeLayerTypeEnum
from cli.functions.helpers import compress_project_to_zip
from cli.functions.helpers import read_manifest_project_file
from cli.functions.helpers import save_manifest_project_file
from cli.functions.models import FunctionGlobalsModel
from cli.functions.models import FunctionModel
from cli.functions.models import FunctionProjectMetadata
from cli.functions.models import FunctionProjectModel
from cli.functions.models import FunctionServerlessModel
from cli.functions.models import FunctionTriggersModel
from cli.settings import settings


class TestFunctionUtils:
    @pytest.fixture(autouse=True)
    def setup(self, mocker, tmp_path):
        self.mocker = mocker
        self.tmp_path = tmp_path
        self.runner = CliRunner()
        self.project_path = tmp_path / "my_function"
        self.project_path.mkdir()

    def create_sample_files(self, root_path):
        subdir = root_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_text("contenido2")
        (root_path / "file1.txt").write_text("contenido1")

    def test_save_manifest_project_file(self):
        # Setup: Define all required parameters.
        engine = FunctionEngineTypeEnum.DOCKER
        language = FunctionLanguageEnum.PYTHON
        # For runtime, we assume a runtime from your Python runtimes (adjust as needed)
        runtime = FunctionRuntimeLayerTypeEnum.PYTHON_3_9_FULL
        label = "my_function"
        name = "my_function"
        methods = []  # empty list for this test
        created_at = "2025-02-18T00:00:00"
        timeout = 30
        http_is_secure = False
        http_enabled = False
        cron = ""
        has_cron = False
        function_id = ""
        token = ""
        params = "{}"

        # Build expected metadata (using your models)
        expected_metadata = FunctionProjectMetadata(
            globals=FunctionGlobalsModel(engine=engine, label=label),
            project=FunctionProjectModel(
                language=language, runtime=runtime, name=name, createdAt=created_at
            ),
            function=FunctionModel(
                label=label,
                id=function_id,
                serverless=FunctionServerlessModel(
                    runtime=runtime,
                    params=params,
                    authToken=token,
                    isRawFunction=False,
                    timeout=timeout,
                ),
                triggers=FunctionTriggersModel(
                    httpMethods=methods,
                    httpHasCors=False,
                    httpIsSecure=False,
                    httpEnabled=False,
                    schedulerCron="",
                    schedulerEnabled=False,
                ),
            ),
        )

        # Action: Call save_manifest_project_file with all parameters.
        save_manifest_project_file(
            name=name,
            project_path=self.project_path,
            language=language,
            runtime=runtime,
            methods=methods,
            label=label,
            created_at=created_at,
            timeout=timeout,
            http_is_secure=http_is_secure,
            http_enabled=http_enabled,
            engine=engine,
            has_cors=False,
            is_raw=False,
            cron=cron,
            has_cron=has_cron,
            function_id=function_id,
            token=token,
            params=params,
        )

        # Assert: Read the metadata file and compare with expected metadata.
        metadata_file = self.project_path / settings.FUNCTIONS.PROJECT_METADATA_FILE
        with open(metadata_file) as file:
            written_metadata = yaml.safe_load(file)

        expected_metadata_dict = expected_metadata.to_yaml_serializable_format()
        # Remove auto-generated "created" if present.
        written_metadata_dict = dict(written_metadata)
        written_metadata_dict["project"].pop("created", None)
        expected_metadata_dict["project"].pop("created", None)
        assert written_metadata_dict == expected_metadata_dict

    def test_read_manifest_project_file(self):
        # Setup
        project_path = self.tmp_path / "fake_project"
        project_path.mkdir()
        language = FunctionLanguageEnum.PYTHON
        runtime = FunctionRuntimeLayerTypeEnum.PYTHON_3_9_FULL
        created_at = "2025-02-18T00:00:00"
        metadata = FunctionProjectMetadata(
            globals=FunctionGlobalsModel(
                engine=FunctionEngineTypeEnum.DOCKER, label="my_function"
            ),
            project=FunctionProjectModel(
                name=project_path.name,
                language=language,
                runtime=runtime,
                createdAt=created_at,  # Required field added
            ),
            function=FunctionModel(
                label="my_function",
                id="",
                serverless=FunctionServerlessModel(
                    runtime=runtime,
                    params="{}",
                    authToken="",
                    isRawFunction=False,
                    timeout=30,
                ),
                triggers=FunctionTriggersModel(
                    httpMethods=[],
                    httpHasCors=False,
                    httpIsSecure=False,
                    httpEnabled=False,
                    schedulerCron="",
                    schedulerEnabled=False,
                ),
            ),
        )
        metadata_file = project_path / settings.FUNCTIONS.PROJECT_METADATA_FILE
        with open(metadata_file, "w") as file:
            yaml.dump(metadata.to_yaml_serializable_format(), file)
        # Action
        read_metadata = read_manifest_project_file(project_path)
        # Assert
        assert read_metadata == metadata

    def test_compress_project_to_zip_includes_directories(self):
        # Setup
        self.create_sample_files(self.tmp_path)
        # Action
        zip_buffer = compress_project_to_zip(self.tmp_path)
        # Assert
        with zipfile.ZipFile(zip_buffer) as zipf:
            all_files_and_dirs = set(zipf.namelist())
            expected_files = {"file1.txt", "subdir/file2.txt"}
            expected_dirs = {"subdir/"}
            assert expected_files.issubset(all_files_and_dirs)
            assert expected_dirs.issubset(all_files_and_dirs)
