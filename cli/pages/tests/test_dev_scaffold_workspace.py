import pytest

from cli.pages.exceptions import PageWithNameAlreadyExistsError
from cli.pages.pipelines.dev_scaffold import CreateProjectFolderStep


def make_data(tmp_path, name="my-page"):
    workspace = tmp_path / ".ubidots_cli" / "pages" / f"{name}-abc12345"
    symlink = tmp_path / "projects" / name
    return {
        "page_name": name,
        "workspace_key": f"{name}-abc12345",
        "project_path": workspace,
        "symlink_path": symlink,
        "verbose": False,
    }


def test_create_project_folder_creates_workspace(tmp_path):
    data = make_data(tmp_path)
    CreateProjectFolderStep().execute(data)
    assert data["project_path"].exists()
    assert data["project_path"].is_dir()


def test_create_project_folder_raises_if_already_exists(tmp_path):
    data = make_data(tmp_path)
    data["project_path"].mkdir(parents=True)  # Directory already exists

    with pytest.raises(PageWithNameAlreadyExistsError):
        CreateProjectFolderStep().execute(data)
