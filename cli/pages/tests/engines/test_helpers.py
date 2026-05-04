# cli/pages/tests/engines/test_helpers.py
from pathlib import Path
from unittest.mock import patch

from cli.pages.engines.helpers import compute_workspace_key
from cli.pages.engines.helpers import deregister_page_from_argo
from cli.pages.engines.helpers import get_page_workspace
from cli.pages.engines.helpers import get_pages_workspace
from cli.pages.engines.helpers import register_page_in_argo

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
