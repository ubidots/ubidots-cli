import hashlib
import logging
import re
import time
from contextlib import suppress
from pathlib import Path

import httpx

from cli.commons.settings import ARGO_API_BASE_PATH

logger = logging.getLogger(__name__)

_ARGO_ALLOWED_EXTENSIONS = [
    ".html",
    ".js",
    ".css",
    ".toml",
    ".json",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".avif",
    ".svg",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".eot",
    ".map",
    ".txt",
    ".md",
]


def compute_workspace_key(page_name: str, page_dir_path: Path) -> str:
    """Return '<page_name>-<8-hex>' stable key from page directory path."""
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", page_name.strip()).strip(".-")
    safe_name = safe_name or "page"
    raw = str(page_dir_path.resolve())
    short = hashlib.sha256(raw.encode()).hexdigest()[:8]
    return f"{safe_name}-{short}"


def get_pages_workspace() -> Path:
    """Return ~/.ubidots_cli/pages/, creating it if needed."""
    path = Path.home() / ".ubidots_cli" / "pages"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_page_workspace(workspace_key: str) -> Path:
    """Return ~/.ubidots_cli/pages/<workspace_key>/, creating it if needed."""
    path = get_pages_workspace() / workspace_key
    path.mkdir(parents=True, exist_ok=True)
    return path


_COPY_EXCLUDED = frozenset(
    {"index.html", ".manifest.yaml", ".pid", ".watcher.pid", ".hot_reload_port"}
)


def get_tracked_files(source_dir: Path) -> list[Path]:
    """Return absolute paths of files to copy from source_dir to workspace.

    Derives the tracked set from manifest.toml per spec rules:
    - body.html and manifest.toml are always tracked
    - js_libraries[*].src, css_libraries[*].href, link_libraries[*].href
      if the path is not http(s)
    - static_paths[*] recursively
    Excludes: index.html, .manifest.yaml, .pid, .watcher.pid, .hot_reload_port
    """
    from cli.pages.models import DashboardPageModel

    source_root = source_dir.resolve()

    def _resolve_local(rel_or_abs: str) -> Path | None:
        candidate = (source_root / rel_or_abs).resolve()
        try:
            candidate.relative_to(source_root)
        except ValueError:
            logger.warning("Ignoring out-of-root tracked path: %s", rel_or_abs)
            return None
        return candidate

    tracked: list[Path] = [
        source_dir / "body.html",
        source_dir / "manifest.toml",
    ]

    try:
        model = DashboardPageModel.load_from_project(source_dir)
    except Exception as exc:
        logger.debug("Could not load manifest from %s: %s", source_dir, exc)
    else:
        assert isinstance(model, DashboardPageModel)
        library_fields = (
            (model.js_libraries, "src"),
            (model.js_thirdparty_libraries, "src"),
            (model.css_libraries, "href"),
            (model.css_thirdparty_libraries, "href"),
            (model.link_libraries, "href"),
            (model.link_thirdparty_libraries, "href"),
        )
        for entries, path_key in library_fields:
            for entry in entries:
                asset_path = entry.get(path_key, "")
                if asset_path and not asset_path.startswith(("http://", "https://")):
                    local = _resolve_local(asset_path)
                    if local:
                        tracked.append(local)

        for static_path in model.static_paths:
            static_abs = _resolve_local(static_path)
            if not static_abs:
                continue
            if static_abs.is_dir():
                tracked.extend(f for f in static_abs.rglob("*") if f.is_file())
            elif static_abs.is_file():
                tracked.append(static_abs)

    return [f for f in tracked if f.is_file() and f.name not in _COPY_EXCLUDED]


def render_index_html(
    source_dir: Path,
    workspace_dir: Path,
    hot_reload_port: int,
) -> None:
    """Render index.html to workspace_dir.

    Reads manifest.toml + body.html from source_dir, writes index.html to
    workspace_dir. BASE_URL is derived from workspace_dir.name (the workspace
    key), which ensures asset paths resolve correctly under Argo routing.
    """
    from cli.pages.helpers import read_page_manifest
    from cli.pages.helpers import render_ubidots_page_index_html
    from cli.pages.models import DashboardPageModel
    from cli.settings import settings

    metadata = read_page_manifest(source_dir)
    page_type = metadata.project.type

    page_model = DashboardPageModel.load_from_project(source_dir)
    page_dict = page_model.model_dump()

    body_file = source_dir / "body.html"
    page_dict["body"] = (
        body_file.read_text(encoding="utf-8") if body_file.exists() else ""
    )

    cdn = settings.PAGES.TEMPLATE_PLACEHOLDERS[page_type.value]
    base_url = f"/{workspace_dir.name}"

    ubidots_html = render_ubidots_page_index_html(
        page=page_dict,
        page_type=page_type,
        BASE_URL=base_url,
        HTML_CANVAS_LIBRARY_URL=cdn["html_canvas_library_url"],
        REACT_URL=cdn["react_url"],
        REACT_DOM_URL=cdn.get("react_dom_url", ""),
        BABEL_STANDALONE_URL=cdn["babel_standalone_url"],
        VULCANUI_JS_URL=cdn["vulcanui_js_url"],
        VULCANUI_CSS_URL=cdn["vulcanui_css_url"],
    )
    final_html = ubidots_html.replace(
        "</body>", f"{_hot_reload_snippet(hot_reload_port)}\n</body>"
    )
    (workspace_dir / "index.html").write_text(final_html, encoding="utf-8")


def _hot_reload_snippet(port: int) -> str:
    return (
        f"<script>\n"
        f"window.onerror=function(m,s,l,c){{fetch('http://localhost:{port}/__dev/error',"
        f"{{method:'POST',body:JSON.stringify({{message:m,source:s,line:l,col:c}})}});}};\n"
        f"var __errBusy=false;"
        f"window.onunhandledrejection=function(e){{"
        f"if(__errBusy)return;__errBusy=true;"
        f"fetch('http://localhost:{port}/__dev/error',"
        f"{{method:'POST',body:JSON.stringify({{message:String(e.reason)}})}})"
        f".finally(function(){{__errBusy=false;}});"
        f"}};\n"
        f"var __s=new EventSource('http://localhost:{port}/__dev/reload');"
        f"__s.onmessage=function(){{window.location.reload();}};\n"
        f"</script>"
    )


def register_page_in_argo(workspace_key: str, argo_admin_port: int) -> None:
    """Register a local_file route for workspace_key in Argo."""
    time.sleep(1)
    payload = {
        "path": workspace_key,
        "label": f"pages-{workspace_key}",
        "is_strict": False,
        "middlewares": [],
        "bridge": {
            "label": f"pages-{workspace_key}",
            "target": {
                "type": "local_file",
                "base_path": f"/pages/{workspace_key}",
                "allowed_extensions": _ARGO_ALLOWED_EXTENSIONS,
            },
        },
    }
    url = f"http://localhost:{argo_admin_port}/{ARGO_API_BASE_PATH}/"
    for attempt in range(2):
        try:
            response = httpx.post(url, json=payload, timeout=10.0)
            response.raise_for_status()
            return
        except httpx.HTTPError:
            if attempt == 1:
                raise
            time.sleep(2)


def deregister_page_from_argo(workspace_key: str, argo_admin_port: int) -> None:
    """Remove the Argo route for workspace_key (best-effort)."""
    with suppress(Exception):
        httpx.delete(
            f"http://localhost:{argo_admin_port}/{ARGO_API_BASE_PATH}/~pages-{workspace_key}"
        )
