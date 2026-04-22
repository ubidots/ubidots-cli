import signal
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from cli.pages.exceptions import PageIsAlreadyRunningError
from cli.pages.exceptions import PageIsAlreadyStoppedError
from cli.pages.pipelines.dev_engine import CopyTrackedFilesStep
from cli.pages.pipelines.dev_engine import CreateWorkspaceStep
from cli.pages.pipelines.dev_engine import DeregisterPageFromArgoStep
from cli.pages.pipelines.dev_engine import FindHotReloadPortStep
from cli.pages.pipelines.dev_engine import GetNetworkStep
from cli.pages.pipelines.dev_engine import GetWorkspaceKeyStep
from cli.pages.pipelines.dev_engine import RegisterPageInArgoStep
from cli.pages.pipelines.dev_engine import RenderIndexHtmlStep
from cli.pages.pipelines.dev_engine import ShowPageLogsStep
from cli.pages.pipelines.dev_engine import StartCopyWatcherStep
from cli.pages.pipelines.dev_engine import StartHotReloadSubprocessStep
from cli.pages.pipelines.dev_engine import StopCopyWatcherStep
from cli.pages.pipelines.dev_engine import StopHotReloadSubprocessStep
from cli.pages.pipelines.dev_engine import ValidatePageDirectoryStep
from cli.pages.pipelines.dev_engine import ValidatePageNotRunningStep
from cli.pages.pipelines.dev_engine import ValidatePageRunningStep


def make_data(**kwargs):
    return {
        "project_path": Path("/tmp/my-page-abc12345"),
        "page_name": "my-page",
        "workspace_key": "my-page-abc12345",
        "argo_adapter_port": 8040,
        "verbose": False,
        **kwargs,
    }


# ── FindHotReloadPortStep ──────────────────────────────────────────────────────


def test_find_hot_reload_port_finds_free_port():
    with patch(
        "cli.pages.pipelines.dev_engine.find_available_ports", return_value=[9001]
    ) as mock:
        data = FindHotReloadPortStep().execute(make_data())
    mock.assert_called_once_with([9000], start_range=9001)
    assert data["hot_reload_port"] == 9001


# ── GetNetworkStep ─────────────────────────────────────────────────────────────


def test_get_network_step_creates_network_if_missing():
    client = MagicMock()
    network_manager = MagicMock()
    network_manager.list.return_value = []
    network = MagicMock()
    network_manager.create.return_value = network
    client.get_network_manager.return_value = network_manager

    data = GetNetworkStep().execute(make_data(client=client))

    network_manager.create.assert_called_once()
    assert data["network"] == network


def test_get_network_step_reuses_existing_network():
    client = MagicMock()
    network_manager = MagicMock()
    existing = MagicMock()
    network_manager.list.return_value = [existing]
    client.get_network_manager.return_value = network_manager

    data = GetNetworkStep().execute(make_data(client=client))

    network_manager.create.assert_not_called()
    assert data["network"] == existing


# ── RegisterPageInArgoStep ─────────────────────────────────────────────────────


def test_register_page_in_argo_step_calls_helper():
    with patch("cli.pages.pipelines.dev_engine.register_page_in_argo") as mock:
        RegisterPageInArgoStep().execute(make_data())
    mock.assert_called_once_with("my-page-abc12345", 8040)


# ── DeregisterPageFromArgoStep ─────────────────────────────────────────────────


def test_deregister_page_step_calls_helper():
    with patch("cli.pages.pipelines.dev_engine.deregister_page_from_argo") as mock:
        DeregisterPageFromArgoStep().execute(make_data())
    mock.assert_called_once_with("my-page-abc12345", 8040)


# ── RenderIndexHtmlStep ────────────────────────────────────────────────────────


def test_render_index_html_step_calls_helper_with_workspace():
    data = make_data(
        project_path=Path("/tmp/source-dir"),
        hot_reload_port=9001,
        workspace_path=Path("/tmp/workspace-key"),
    )
    with patch("cli.pages.pipelines.dev_engine.render_index_html") as mock:
        RenderIndexHtmlStep().execute(data)
    # Called with (source_dir, workspace_dir, port) — two distinct paths
    mock.assert_called_once_with(
        Path("/tmp/source-dir"),
        Path("/tmp/workspace-key"),
        9001,
    )


# ── StartHotReloadSubprocessStep ───────────────────────────────────────────────


def test_start_hot_reload_step_uses_workspace_for_log_and_arg(tmp_path):
    source = tmp_path / "source"
    workspace = tmp_path / "workspace"
    source.mkdir()
    workspace.mkdir()
    mock_proc = MagicMock()
    mock_proc.pid = 12345

    data = make_data(
        project_path=source, workspace_path=workspace, hot_reload_port=9001
    )
    with patch(
        "cli.pages.pipelines.dev_engine.subprocess.Popen", return_value=mock_proc
    ) as mock_popen:
        StartHotReloadSubprocessStep().execute(data)

    # .hot_reload.log goes to workspace, not source
    assert (workspace / ".hot_reload.log").exists()
    assert not (source / ".hot_reload.log").exists()
    # --page-workspace arg uses workspace_path
    cmd = mock_popen.call_args[0][0]
    assert str(workspace) in cmd
    # .pid goes to source dir
    assert (source / ".pid").read_text() == "12345"


# ── StopHotReloadSubprocessStep ────────────────────────────────────────────────


def test_stop_hot_reload_subprocess_waits_for_exit(tmp_path):
    workspace = tmp_path / "my-page-abc12345"
    workspace.mkdir()
    pid_file = workspace / ".pid"
    pid_file.write_text("99999")

    call_count = [0]

    def fake_kill(pid, sig):
        call_count[0] += 1
        if call_count[0] >= 3:
            raise ProcessLookupError

    with patch("os.kill", side_effect=fake_kill):
        StopHotReloadSubprocessStep().execute(make_data(project_path=workspace))

    assert not pid_file.exists()
    assert call_count[0] >= 2  # at least SIGTERM + one poll


# ── ShowPageLogsStep ───────────────────────────────────────────────────────────


def test_show_page_logs_step_reads_from_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / ".copy_watcher.log").write_text("log line")
    (workspace / ".hot_reload.log").write_text("startup line")

    data = make_data(
        project_path=tmp_path / "source",
        workspace_path=workspace,
        tail="all",
        follow=False,
    )
    with patch("cli.pages.pipelines.dev_engine.subprocess.run") as mock_run:
        ShowPageLogsStep().execute(data)

    cmd = mock_run.call_args[0][0]
    assert str(workspace / ".copy_watcher.log") in cmd
    assert str(workspace / ".hot_reload.log") in cmd


# ── StartCopyWatcherStep / StopCopyWatcherStep ─────────────────────────────────


def test_start_copy_watcher_step_writes_watcher_pid(tmp_path):
    source = tmp_path / "my-page"
    source.mkdir()
    workspace = tmp_path / "my-page-abc12345"
    workspace.mkdir()
    mock_proc = MagicMock()
    mock_proc.pid = 55555

    data = make_data(project_path=source, workspace_path=workspace)
    with patch(
        "cli.pages.pipelines.dev_engine.subprocess.Popen", return_value=mock_proc
    ):
        StartCopyWatcherStep().execute(data)

    watcher_pid = source / ".watcher.pid"
    assert watcher_pid.exists()
    assert watcher_pid.read_text() == "55555"


def test_stop_copy_watcher_step_sigterms_and_removes_pid(tmp_path):
    source = tmp_path / "my-page"
    source.mkdir()
    watcher_pid = source / ".watcher.pid"
    watcher_pid.write_text("77777")

    data = make_data(project_path=source)
    with patch("os.kill") as mock_kill:
        # Make os.kill(pid, 0) raise ProcessLookupError immediately so the wait exits
        mock_kill.side_effect = [None, ProcessLookupError]
        StopCopyWatcherStep().execute(data)

    mock_kill.assert_any_call(77777, signal.SIGTERM)
    assert not watcher_pid.exists()


def test_stop_copy_watcher_step_noop_when_no_pid(tmp_path):
    source = tmp_path / "my-page"
    source.mkdir()
    StopCopyWatcherStep().execute(make_data(project_path=source))  # no error


# ── ValidatePageNotRunningStep ─────────────────────────────────────────────────


def test_validate_page_not_running_passes_when_no_pid(tmp_path):
    workspace = tmp_path / "my-page-abc12345"
    workspace.mkdir()
    # No .pid file
    ValidatePageNotRunningStep().execute(make_data(project_path=workspace))  # no error


def test_validate_page_not_running_raises_when_pid_exists(tmp_path):
    workspace = tmp_path / "my-page-abc12345"
    workspace.mkdir()
    (workspace / ".pid").write_text("12345")
    with patch("os.kill"), pytest.raises(
        PageIsAlreadyRunningError
    ):  # don't actually kill anything
        ValidatePageNotRunningStep().execute(make_data(project_path=workspace))


# ── ValidatePageRunningStep ────────────────────────────────────────────────────


def test_validate_page_running_passes_when_pid_exists(tmp_path):
    workspace = tmp_path / "my-page-abc12345"
    workspace.mkdir()
    (workspace / ".pid").write_text("12345")
    with patch("os.kill"):
        ValidatePageRunningStep().execute(make_data(project_path=workspace))  # no error


def test_validate_page_running_raises_when_no_pid(tmp_path):
    workspace = tmp_path / "my-page-abc12345"
    workspace.mkdir()
    with pytest.raises(PageIsAlreadyStoppedError):
        ValidatePageRunningStep().execute(make_data(project_path=workspace))


# ── GetWorkspaceKeyStep ────────────────────────────────────────────────────────


def test_get_workspace_key_step_sets_workspace_path_not_project_path(tmp_path):
    source = tmp_path / "my-page"
    source.mkdir()
    data = {
        "project_path": source,
        "page_name": "my-page",
        "verbose": False,
    }
    with patch(
        "cli.pages.pipelines.dev_engine.get_pages_workspace", return_value=tmp_path
    ):
        result = GetWorkspaceKeyStep().execute(data)

    assert result["project_path"] == source  # unchanged
    assert result["workspace_key"].startswith("my-page-")
    assert result["workspace_path"] == tmp_path / result["workspace_key"]


def test_get_workspace_key_step_key_is_deterministic(tmp_path):
    source = tmp_path / "my-page"
    source.mkdir()
    data = {"project_path": source, "page_name": "my-page", "verbose": False}
    with patch(
        "cli.pages.pipelines.dev_engine.get_pages_workspace", return_value=tmp_path
    ):
        r1 = GetWorkspaceKeyStep().execute(data.copy())
        r2 = GetWorkspaceKeyStep().execute(data.copy())
    assert r1["workspace_key"] == r2["workspace_key"]


# ── ValidatePageDirectoryStep ──────────────────────────────────────────────────


def test_validate_page_directory_step_passes_on_symlink_with_manifest(tmp_path):
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    (real_dir / "manifest.toml").write_text("")
    symlink = tmp_path / "my-page"
    symlink.symlink_to(real_dir)

    # Symlink check removed — only manifest presence matters now
    ValidatePageDirectoryStep().execute({"project_path": symlink})  # no error


def test_validate_page_directory_step_passes_on_plain_dir(tmp_path):
    page_dir = tmp_path / "my-page"
    page_dir.mkdir()
    (page_dir / "manifest.toml").write_text("")
    ValidatePageDirectoryStep().execute({"project_path": page_dir})  # no error


# ── CreateWorkspaceStep ────────────────────────────────────────────────────────


def test_create_workspace_step_creates_directory(tmp_path):
    source = tmp_path / "my-page"
    source.mkdir()
    workspace = tmp_path / "my-page-abc12345"
    data = make_data(project_path=source, workspace_path=workspace)
    CreateWorkspaceStep().execute(data)
    assert workspace.is_dir()
    assert (workspace / ".source_path").read_text() == str(source)


def test_create_workspace_step_ok_if_exists(tmp_path):
    source = tmp_path / "my-page"
    source.mkdir()
    workspace = tmp_path / "my-page-abc12345"
    workspace.mkdir()
    CreateWorkspaceStep().execute(
        make_data(project_path=source, workspace_path=workspace)
    )  # no error


# ── CopyTrackedFilesStep ────────────────────────────────────────────────────────


def test_copy_tracked_files_step_copies_body_html(tmp_path):
    source = tmp_path / "source"
    workspace = tmp_path / "workspace"
    source.mkdir()
    workspace.mkdir()
    (source / "body.html").write_text("<p>hello</p>")
    (source / "manifest.toml").write_text(
        '[page]\nname = "p"\n[page.js_libraries]\n[page.css_libraries]\n'
    )

    data = make_data(project_path=source, workspace_path=workspace)
    CopyTrackedFilesStep().execute(data)

    assert (workspace / "body.html").read_text() == "<p>hello</p>"


def test_copy_tracked_files_step_skips_index_html(tmp_path):
    source = tmp_path / "source"
    workspace = tmp_path / "workspace"
    source.mkdir()
    workspace.mkdir()
    (source / "body.html").write_text("")
    (source / "index.html").write_text("generated")
    (source / "manifest.toml").write_text(
        '[page]\nname = "p"\n[page.js_libraries]\n[page.css_libraries]\n'
    )

    CopyTrackedFilesStep().execute(
        make_data(project_path=source, workspace_path=workspace)
    )

    assert not (workspace / "index.html").exists()
