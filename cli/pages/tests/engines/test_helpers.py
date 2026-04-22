# cli/pages/tests/engines/test_helpers.py
from pathlib import Path
from unittest.mock import patch

from cli.pages.engines.helpers import compute_workspace_key
from cli.pages.engines.helpers import deregister_page_from_argo
from cli.pages.engines.helpers import get_page_workspace
from cli.pages.engines.helpers import get_pages_workspace
from cli.pages.engines.helpers import get_tracked_files
from cli.pages.engines.helpers import register_page_in_argo
from cli.pages.engines.helpers import render_index_html

# ── compute_workspace_key ──────────────────────────────────────────────────────


def test_compute_workspace_key_format():
    key = compute_workspace_key("my-page", Path("/some/dir/my-page"))
    assert key.startswith("my-page-")
    suffix = key[len("my-page-") :]
    assert len(suffix) == 8
    assert all(c in "0123456789abcdef" for c in suffix)


def test_compute_workspace_key_deterministic():
    path = Path("/home/dev/projects/my-page")
    assert compute_workspace_key("my-page", path) == compute_workspace_key(
        "my-page", path
    )


def test_compute_workspace_key_differs_by_path():
    key1 = compute_workspace_key("my-page", Path("/some-dir/my-page"))
    key2 = compute_workspace_key("my-page", Path("/another-dir/my-page"))
    assert key1 != key2


def test_compute_workspace_key_differs_by_name():
    path = Path("/some-dir/page")
    key1 = compute_workspace_key("page-a", path)
    key2 = compute_workspace_key("page-b", path)
    assert key1 != key2


# ── get_pages_workspace ────────────────────────────────────────────────────────


def test_get_pages_workspace_returns_expected_path(tmp_path):
    with patch("cli.pages.engines.helpers.Path.home", return_value=tmp_path):
        result = get_pages_workspace()
    assert result == tmp_path / ".ubidots_cli" / "pages"
    assert result.exists()


# ── get_page_workspace ─────────────────────────────────────────────────────────


def test_get_page_workspace_creates_directory(tmp_path):
    with patch("cli.pages.engines.helpers.Path.home", return_value=tmp_path):
        result = get_page_workspace("my-page-abc12345")
    assert result == tmp_path / ".ubidots_cli" / "pages" / "my-page-abc12345"
    assert result.exists()


# ── register_page_in_argo ──────────────────────────────────────────────────────


def test_register_page_in_argo_posts_correct_payload():
    with (
        patch("cli.pages.engines.helpers.httpx.post") as mock_post,
        patch("cli.pages.engines.helpers.time.sleep"),
    ):
        register_page_in_argo("my-page-abc12345", 8040)

    mock_post.assert_called_once()
    url = mock_post.call_args.args[0]
    payload = mock_post.call_args.kwargs["json"]

    assert url == "http://localhost:8040/api/_/route/"  # trailing slash
    assert payload["path"] == "my-page-abc12345"
    assert payload["label"] == "pages-my-page-abc12345"
    assert payload["is_strict"] is False
    assert payload["middlewares"] == []
    assert payload["bridge"]["label"] == "pages-my-page-abc12345"
    assert payload["bridge"]["target"]["type"] == "local_file"
    assert payload["bridge"]["target"]["base_path"] == "/pages/my-page-abc12345"
    assert ".html" in payload["bridge"]["target"]["allowed_extensions"]


# ── deregister_page_from_argo ──────────────────────────────────────────────────


def test_deregister_page_from_argo_sends_delete():
    with patch("cli.pages.engines.helpers.httpx.delete") as mock_delete:
        deregister_page_from_argo("my-page-abc12345", 8040)

    mock_delete.assert_called_once_with(
        "http://localhost:8040/api/_/route/~pages-my-page-abc12345"
    )


def test_compute_workspace_key_param_name_is_page_dir_path():
    """Parameter rename: symlink_path → page_dir_path — logic unchanged."""
    key = compute_workspace_key("my-page", Path("/some/dir/my-page"))
    assert key.startswith("my-page-")


def test_get_tracked_files_always_includes_body_and_manifest(tmp_path):
    (tmp_path / "body.html").write_text("<p/>")
    (tmp_path / "manifest.toml").write_text(
        '[page]\nname = "p"\njs_libraries = []\ncss_libraries = []\n'
    )
    files = get_tracked_files(tmp_path)
    names = {f.name for f in files}
    assert "body.html" in names
    assert "manifest.toml" in names


def test_get_tracked_files_includes_local_js_href(tmp_path):
    (tmp_path / "body.html").write_text("")
    (tmp_path / "script.js").write_text("")
    (tmp_path / "manifest.toml").write_text(
        '[page]\nname = "p"\ncss_libraries = []\n[[page.js_libraries]]\nsrc = "script.js"\n'
    )
    files = get_tracked_files(tmp_path)
    names = {f.name for f in files}
    assert "script.js" in names


def test_get_tracked_files_excludes_http_urls(tmp_path):
    (tmp_path / "body.html").write_text("")
    (tmp_path / "manifest.toml").write_text(
        '[page]\nname = "p"\ncss_libraries = []\n[[page.js_libraries]]\nsrc = "https://cdn.example.com/lib.js"\n'
    )
    files = get_tracked_files(tmp_path)
    names = {f.name for f in files}
    assert "lib.js" not in names


def test_get_tracked_files_includes_static_paths_recursively(tmp_path):
    (tmp_path / "body.html").write_text("")
    static = tmp_path / "static"
    static.mkdir()
    (static / "data.js").write_text("{}")
    (tmp_path / "manifest.toml").write_text(
        '[page]\nname = "p"\nstatic_paths = ["static"]\njs_libraries = []\ncss_libraries = []\n'
    )
    files = get_tracked_files(tmp_path)
    names = {f.name for f in files}
    assert "data.js" in names


def test_get_tracked_files_excludes_index_html(tmp_path):
    (tmp_path / "body.html").write_text("")
    (tmp_path / "index.html").write_text("")
    (tmp_path / "manifest.toml").write_text(
        '[page]\nname = "p"\njs_libraries = []\ncss_libraries = []\n'
    )
    files = get_tracked_files(tmp_path)
    names = {f.name for f in files}
    assert "index.html" not in names


def test_render_index_html_new_signature_writes_to_workspace(tmp_path):
    source = tmp_path / "source"
    workspace = tmp_path / "workspace"
    source.mkdir()
    workspace.mkdir()

    from unittest.mock import MagicMock
    from unittest.mock import patch

    mock_metadata = MagicMock()
    mock_metadata.project.type.value = "dashboard"
    mock_page_model = MagicMock()
    mock_page_model.model_dump.return_value = {"body": ""}

    with (
        patch("cli.pages.helpers.read_page_manifest", return_value=mock_metadata),
        patch("cli.pages.models.DashboardPageModel") as MockModel,
        patch(
            "cli.pages.helpers.render_ubidots_page_index_html",
            return_value="<html></body>",
        ),
        patch("cli.settings.settings") as mock_settings,
    ):
        mock_settings.PAGES.TEMPLATE_PLACEHOLDERS = {
            "dashboard": {
                "html_canvas_library_url": "",
                "react_url": "",
                "react_dom_url": "",
                "babel_standalone_url": "",
                "vulcanui_js_url": "",
                "vulcanui_css_url": "",
            }
        }
        MockModel.load_from_project.return_value = mock_page_model
        (source / "body.html").write_text("<p/>")
        render_index_html(source, workspace, 9001)

        result = build_pages_image_if_needed()

        self.assertFalse(result)

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_build_pages_image_if_needed_subprocess_check_error(
        self, mock_exists, mock_subprocess_run
    ):
        """Test building pages image when subprocess check fails."""
        mock_exists.return_value = True
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, "cmd")

        result = build_pages_image_if_needed()

        self.assertFalse(result)


# ── Workspace helper tests (Argo-based architecture) ──────────────────────────

from pathlib import Path  # noqa: E402
from unittest.mock import patch  # noqa: E402

from cli.pages.engines.helpers import compute_workspace_key  # noqa: E402
from cli.pages.engines.helpers import deregister_page_from_argo  # noqa: E402
from cli.pages.engines.helpers import get_page_workspace  # noqa: E402
from cli.pages.engines.helpers import get_pages_workspace  # noqa: E402
from cli.pages.engines.helpers import get_tracked_files  # noqa: E402
from cli.pages.engines.helpers import register_page_in_argo  # noqa: E402


def test_compute_workspace_key_format():
    key = compute_workspace_key("my-page", Path("/some/dir/my-page"))
    assert key.startswith("my-page-")
    suffix = key[len("my-page-") :]
    assert len(suffix) == 8
    assert all(c in "0123456789abcdef" for c in suffix)


def test_compute_workspace_key_deterministic():
    path = Path("/home/dev/projects/my-page")
    assert compute_workspace_key("my-page", path) == compute_workspace_key(
        "my-page", path
    )


def test_compute_workspace_key_differs_by_path():
    assert compute_workspace_key(
        "my-page", Path("/a/my-page")
    ) != compute_workspace_key("my-page", Path("/b/my-page"))


def test_compute_workspace_key_differs_by_name():
    path = Path("/some-dir/page")
    assert compute_workspace_key("page-a", path) != compute_workspace_key(
        "page-b", path
    )


def test_get_pages_workspace_returns_expected_path(tmp_path):
    with patch("cli.pages.engines.helpers.Path.home", return_value=tmp_path):
        result = get_pages_workspace()
    assert result == tmp_path / ".ubidots_cli" / "pages"
    assert result.exists()


def test_get_page_workspace_creates_directory(tmp_path):
    with patch("cli.pages.engines.helpers.Path.home", return_value=tmp_path):
        result = get_page_workspace("my-page-abc12345")
    assert result == tmp_path / ".ubidots_cli" / "pages" / "my-page-abc12345"
    assert result.exists()


def test_register_page_in_argo_posts_correct_payload():
    with (
        patch("cli.pages.engines.helpers.httpx.post") as mock_post,
        patch("cli.pages.engines.helpers.time.sleep"),
    ):
        register_page_in_argo("my-page-abc12345", 8040)

    mock_post.assert_called_once()
    url = mock_post.call_args.args[0]
    payload = mock_post.call_args.kwargs["json"]
    assert url == "http://localhost:8040/api/_/route/"
    assert payload["path"] == "my-page-abc12345"
    assert payload["label"] == "pages-my-page-abc12345"
    assert payload["is_strict"] is False
    assert payload["bridge"]["target"]["type"] == "local_file"
    assert payload["bridge"]["target"]["base_path"] == "/pages/my-page-abc12345"
    assert ".html" in payload["bridge"]["target"]["allowed_extensions"]


def test_deregister_page_from_argo_sends_delete():
    with patch("cli.pages.engines.helpers.httpx.delete") as mock_delete:
        deregister_page_from_argo("my-page-abc12345", 8040)
    mock_delete.assert_called_once_with(
        "http://localhost:8040/api/_/route/~pages-my-page-abc12345"
    )


def test_get_tracked_files_always_includes_body_and_manifest(tmp_path):
    (tmp_path / "body.html").write_text("<p/>")
    (tmp_path / "manifest.toml").write_text(
        '[page]\nname = "p"\njs_libraries = []\ncss_libraries = []\n'
    )
    names = {f.name for f in get_tracked_files(tmp_path)}
    assert "body.html" in names
    assert "manifest.toml" in names


def test_get_tracked_files_includes_local_js_src(tmp_path):
    (tmp_path / "body.html").write_text("")
    (tmp_path / "script.js").write_text("")
    (tmp_path / "manifest.toml").write_text(
        '[page]\nname = "p"\ncss_libraries = []\n[[page.js_libraries]]\nsrc = "script.js"\n'
    )
    assert "script.js" in {f.name for f in get_tracked_files(tmp_path)}


def test_get_tracked_files_excludes_http_urls(tmp_path):
    (tmp_path / "body.html").write_text("")
    (tmp_path / "manifest.toml").write_text(
        '[page]\nname = "p"\ncss_libraries = []\n[[page.js_libraries]]\nsrc = "https://cdn.example.com/lib.js"\n'
    )
    assert "lib.js" not in {f.name for f in get_tracked_files(tmp_path)}


def test_get_tracked_files_includes_static_paths_recursively(tmp_path):
    (tmp_path / "body.html").write_text("")
    static = tmp_path / "static"
    static.mkdir()
    (static / "data.js").write_text("{}")
    (tmp_path / "manifest.toml").write_text(
        '[page]\nname = "p"\nstatic_paths = ["static"]\njs_libraries = []\ncss_libraries = []\n'
    )
    assert "data.js" in {f.name for f in get_tracked_files(tmp_path)}


def test_get_tracked_files_excludes_index_html(tmp_path):
    (tmp_path / "body.html").write_text("")
    (tmp_path / "index.html").write_text("")
    (tmp_path / "manifest.toml").write_text(
        '[page]\nname = "p"\njs_libraries = []\ncss_libraries = []\n'
    )
    assert "index.html" not in {f.name for f in get_tracked_files(tmp_path)}
