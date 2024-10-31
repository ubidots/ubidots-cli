import zipfile
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.enums import FunctionPythonRuntimeLayerTypeEnum
from cli.functions.helpers import compress_project_to_zip
from cli.functions.helpers import read_manifest_project_file
from cli.functions.helpers import save_manifest_project_file
from cli.functions.models import FunctionGlobals
from cli.functions.models import FunctionInfo
from cli.functions.models import FunctionProjectInfo
from cli.functions.models import FunctionProjectMetadata
from cli.settings import settings


class TestFunctionUtils:
    @pytest.fixture(autouse=True)
    def setup(self, mocker, tmp_path):
        self.mocker = mocker
        self.tmp_path = tmp_path
        self.runner = CliRunner()
        self.project_path = Path("/my_function")

    def create_sample_files(self, root_path):
        subdir = root_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_text("contenido2")
        (root_path / "file1.txt").write_text("contenido1")

    def test_save_manifest_project_file(self):
        # Setup
        project_path = self.tmp_path / "fake_project"
        project_path.mkdir()
        engine = FunctionEngineTypeEnum.DOCKER
        language = FunctionLanguageEnum.PYTHON
        runtime = FunctionPythonRuntimeLayerTypeEnum.PYTHON_3_9_FULL
        expected_metadata = FunctionProjectMetadata(
            globals=FunctionGlobals(),
            project=FunctionProjectInfo(
                name=project_path.name,
                local_label="my_function",
                language=language,
                runtime=runtime,
            ),
            function=FunctionInfo(id=""),
        )
        # Action
        save_manifest_project_file(
            project_path=project_path,
            engine=engine,
            local_label="my_function",
            language=language,
            runtime=runtime,
        )
        # Assert
        metadata_file = project_path / settings.FUNCTIONS.PROJECT_METADATA_FILE
        with open(metadata_file) as file:
            written_metadata = yaml.safe_load(file)
        expected_metadata_dict = expected_metadata.to_yaml_serializable_format()
        written_metadata_dict = dict(written_metadata)
        written_metadata_dict["project"].pop("created", None)
        expected_metadata_dict["project"].pop("created", None)
        assert written_metadata_dict == expected_metadata_dict

    def test_read_manifest_project_file(self):
        # Setup
        project_path = self.tmp_path / "fake_project"
        project_path.mkdir()
        language = FunctionLanguageEnum.PYTHON
        runtime = FunctionPythonRuntimeLayerTypeEnum.PYTHON_3_9_FULL
        metadata = FunctionProjectMetadata(
            globals=FunctionGlobals(),
            project=FunctionProjectInfo(
                name=project_path.name, language=language, runtime=runtime
            ),
            function=FunctionInfo(id=""),
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
