from cli.pages.pipelines.sync import CreatePullDirectoryStep


def test_create_pull_directory_step_new_pull_creates_dir(tmp_path):
    """New pull: creates project_path/page-name/ and updates data['project_path']."""
    data = {
        "is_new_page_pull": True,
        "project_path": tmp_path,
        "remote_page_detail": {"name": "my-page"},
    }
    result = CreatePullDirectoryStep().execute(data)
    expected = tmp_path / "my-page"
    assert expected.is_dir()
    assert result["project_path"] == expected


def test_create_pull_directory_step_existing_pull_unchanged(tmp_path):
    """Existing pull: project_path is unchanged and no new directory is created."""
    data = {
        "is_new_page_pull": False,
        "project_path": tmp_path,
        "remote_page_detail": {"name": "my-page"},
    }
    before = set(tmp_path.iterdir())
    result = CreatePullDirectoryStep().execute(data)
    after = set(tmp_path.iterdir())
    assert result["project_path"] == tmp_path
    assert before == after
