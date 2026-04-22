import re
import subprocess
import sys
import hashlib
import logging
import time
import httpx
from contextlib import suppress
from pathlib import Path

from docker.errors import ImageNotFound
from docker.errors import NotFound

from cli.pages.engines.docker.client import PageDockerClient
from cli.pages.engines.docker.container import PageDockerContainerManager
from cli.pages.engines.enums import ContainerStatusEnum
from cli.pages.engines.exceptions import ContainerNotFoundException
from cli.pages.engines.settings import page_engine_settings
from cli.settings import settings
from cli.commons.settings import ARGO_API_BASE_PATH


def get_or_create_pages_network(client: PageDockerClient):
    """Get existing pages network or create it if it doesn't exist"""
    network_manager = client.get_network_manager()
    networks = network_manager.list()
    network = next(iter(networks), None)

    if not network:
        network = network_manager.create()

    return network


def build_pages_image_if_needed() -> bool:
    """
    Build the custom Docker image if it doesn't exist.
    Returns True if image is available (built or already exists), False if build failed.
    """
    # Get the build script path
    build_script = Path(__file__).parent / "docker" / "build_image.py"

    if not build_script.exists():
        print(f"Warning: Build script not found at {build_script}")
        return False

    try:
        # print("🔨 Building custom Docker image for faster page startup...")
        print("Building server image...")
        # print("   This is a one-time setup that will make future page starts instant.")

        subprocess.run(
            [sys.executable, str(build_script)],
            check=True,
            capture_output=True,
            text=True,
        )

        return True

    except subprocess.CalledProcessError as e:
        print("⚠️  Failed to build custom Docker image:")
        if e.stderr:
            print(f"   {e.stderr.strip()}")
        print("   Pages will use fallback mode (slower startup but still functional)")
        return False
    except Exception as e:
        print(f"⚠️  Unexpected error building image: {e}")
        print("   Pages will use fallback mode (slower startup but still functional)")
        return False


def get_available_page_image(client: PageDockerClient, auto_build: bool = False) -> str:
    """
    Get the best available Docker image for page containers.
    Returns custom image if available, otherwise fallback image.

    Args:
        client: Docker client
        auto_build: If True, attempt to build custom image if it doesn't exist
    """
    try:
        # Try to get the custom image
        client.client.images.get(page_engine_settings.PYTHON_IMAGE)
        return page_engine_settings.PYTHON_IMAGE
    except ImageNotFound:
        if auto_build and build_pages_image_if_needed():
            # Check if build was successful
            try:
                client.client.images.get(page_engine_settings.PYTHON_IMAGE)
                return page_engine_settings.PYTHON_IMAGE
            except ImageNotFound:
                pass  # Build failed, fall back

        # Fall back to the standard Python image
        return page_engine_settings.FALLBACK_PYTHON_IMAGE


def flask_manager_container_helper(
    container_manager: PageDockerContainerManager,
    client: PageDockerClient,
    network,
    flask_manager_path: Path,
):
    """
    Manage the Flask manager container (similar to Argo in functions module).

    This container acts as the central reverse proxy that routes requests
    to individual page containers based on subdomain.
    """
    container_name = page_engine_settings.CONTAINER.FLASK_MANAGER.NAME

    def check_container_status():
        """Check if Flask manager is already running"""
        container = None
        with suppress(NotFound):
            container = client.client.containers.get(container_name)

        if container is None:
            return None

        # If paused or exited, remove it so it gets recreated with the current command
        if container.status in [ContainerStatusEnum.PAUSED, ContainerStatusEnum.EXITED]:
            with suppress(Exception):
                container.remove()
            return None

        # If running, return it
        if container.status == ContainerStatusEnum.RUNNING:
            return container

        return container

    # Check if already running
    container = check_container_status()
    if container is not None:
        return container

    # Start new Flask manager container
    return container_manager.start(
        image_name=page_engine_settings.PYTHON_IMAGE,
        container_name=container_name,
        network_name=network.name,
        labels={page_engine_settings.CONTAINER.FLASK_MANAGER.LABEL_KEY: "true"},
        ports={
            page_engine_settings.CONTAINER.FLASK_MANAGER.INTERNAL_PORT: (
                page_engine_settings.HOST_BIND,
                page_engine_settings.CONTAINER.FLASK_MANAGER.EXTERNAL_PORT,
            )
        },
        environment={
            "ROUTING_MODE": settings.PAGES.ROUTING_MODE,
        },
        volumes={
            "/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "ro"},
            str(flask_manager_path): {"bind": "/app/manager.py", "mode": "ro"},
        },
        command="python /app/manager.py",
        hostname=page_engine_settings.CONTAINER.FLASK_MANAGER.HOSTNAME,
        user="root",
    )


def get_next_available_port(
    container_manager: PageDockerContainerManager, start_port: int = 8090
):
    """Find the next available external port for page containers"""
    used_ports = set()

    # Get all existing page containers and their ports
    try:
        containers = container_manager.list(filters={"label": "ubidots_cli_page=true"})
        for container in containers:
            # Extract external port from container port mappings
            if hasattr(container, "ports") and container.ports:
                for port_mapping in container.ports.values():
                    if port_mapping:
                        for mapping in port_mapping:
                            if mapping.get("HostPort"):
                                used_ports.add(int(mapping["HostPort"]))
    except Exception as e:
        print(f"Warning: Could not check existing ports: {e}")

    # Find next available port
    port = start_port
    while port in used_ports:
        port += 1

    return port


def page_container_helper(
    container_manager: PageDockerContainerManager,
    network,
    page_name: str,
    page_path: Path,
    page_server_path: Path,
    client: PageDockerClient,
):
    """
    Manage individual page containers (similar to FRIE in functions module).

    Each page gets its own container running a Flask static file server.
    The container is labeled with subdomain and upstream information for routing.

    Returns:
        tuple: (container, subdomain, url)
    """
    # Get routing mode from settings
    routing_mode = settings.PAGES.ROUTING_MODE

    # Sanitize page name for container and subdomain
    sanitized_name = page_name.replace(" ", "-")
    container_name = (
        f"{page_engine_settings.CONTAINER.PAGE.PREFIX_NAME}-{sanitized_name}"
    )
    subdomain = sanitized_name
    upstream = f"{container_name}:{page_engine_settings.CONTAINER.PAGE.INTERNAL_PORT}"

    # Configure based on routing mode
    if routing_mode == "subdomain":
        # Subdomain mode: no external port allocation for main service
        external_port = None
        url = f"http://{subdomain}.localhost:{page_engine_settings.CONTAINER.FLASK_MANAGER.EXTERNAL_PORT}/"

        # Always allocate a port for hot reload (separate from main service)
        hot_reload_port = get_next_available_port(container_manager, start_port=9000)
        ports_config = {
            f"{page_engine_settings.CONTAINER.PAGE.INTERNAL_PORT + 1}/tcp": (
                "127.0.0.1",
                hot_reload_port,
            )
        }

    elif routing_mode == "port":
        # Port mode: allocate external port, no subdomain
        external_port = get_next_available_port(container_manager)
        url = f"http://localhost:{external_port}/"

        # For port mode, hot reload uses the same port as main service
        hot_reload_port = external_port
        ports_config = {
            f"{page_engine_settings.CONTAINER.PAGE.INTERNAL_PORT}/tcp": (
                "127.0.0.1",
                external_port,
            )
        }

    elif routing_mode == "path":
        # Path mode: no external port allocation for main service
        external_port = None
        url = f"http://localhost:{page_engine_settings.CONTAINER.FLASK_MANAGER.EXTERNAL_PORT}/{sanitized_name}"

        # Always allocate a port for hot reload (separate from main service)
        hot_reload_port = get_next_available_port(container_manager, start_port=9000)
        ports_config = {
            f"{page_engine_settings.CONTAINER.PAGE.INTERNAL_PORT + 1}/tcp": (
                "127.0.0.1",
                hot_reload_port,
            )
        }

    else:
        msg = f"Invalid routing mode: {routing_mode}"
        raise ValueError(msg)

    def check_container_status():
        """Check if page container is already running"""
        container = None
        try:
            container = container_manager.get(container_name)
        except ContainerNotFoundException:
            return None

        if container is None:
            return None

        if container.status == ContainerStatusEnum.RUNNING:
            return container

        return None

    # Check if already running
    container = check_container_status()
    if container is not None:
        return container, subdomain, url

    # Get template path
    template_path = (
        Path(__file__).parent.parent / "templates" / "ubidots-page.html.template"
    )

    # Get CDN URLs from settings
    cdn_urls = settings.PAGES.TEMPLATE_PLACEHOLDERS["dashboard"]

    # Get the best available Docker image (auto-build if needed)
    image_name = get_available_page_image(client, auto_build=True)

    # Determine command based on image type
    if image_name == page_engine_settings.PYTHON_IMAGE:
        # Custom image with pre-installed dependencies
        command = "python /app/server.py"
    else:
        # Fallback image - need to install dependencies
        command = "sh -c 'cd /app/page && pip install -q flask tomli flask-cors && python /app/server.py'"

    # Prepare container configuration
    container_config = {
        "image_name": image_name,
        "container_name": container_name,
        "network_name": network.name,
        "labels": {
            page_engine_settings.CONTAINER.PAGE.LABEL_KEY: "true",
            page_engine_settings.CONTAINER.PAGE.SUBDOMAIN_LABEL_KEY: subdomain,
            page_engine_settings.CONTAINER.PAGE.UPSTREAM_LABEL_KEY: upstream,
            page_engine_settings.CONTAINER.PAGE.PATH_LABEL_KEY: str(
                page_path.absolute()
            ),
        },
        "environment": {
            "PAGE_NAME": sanitized_name,
            "ROUTING_MODE": routing_mode,
            "FLASK_MANAGER_PORT": str(
                page_engine_settings.CONTAINER.FLASK_MANAGER.EXTERNAL_PORT
            ),
            "HTML_CANVAS_LIBRARY_URL": cdn_urls["html_canvas_library_url"],
            "REACT_URL": cdn_urls["react_url"],
            "REACT_DOM_URL": cdn_urls["react_dom_url"],
            "BABEL_STANDALONE_URL": cdn_urls["babel_standalone_url"],
            "VULCANUI_JS_URL": cdn_urls["vulcanui_js_url"],
            "VULCANUI_CSS_URL": cdn_urls["vulcanui_css_url"],
            # Hot reload configuration
            "HOT_RELOAD_ENABLED": str(settings.PAGES.HOT_RELOAD_ENABLED),
            "HOT_RELOAD_ENDPOINT": settings.PAGES.HOT_RELOAD_ENDPOINT,
            "HOT_RELOAD_PORT": str(hot_reload_port),
            "HOT_RELOAD_WATCH_EXTENSIONS": ",".join(
                settings.PAGES.HOT_RELOAD_WATCH_EXTENSIONS
            ),
            "HOT_RELOAD_IGNORE_PATTERNS": ",".join(
                settings.PAGES.HOT_RELOAD_IGNORE_PATTERNS
            ),
            "HOT_RELOAD_DEBOUNCE_MS": str(settings.PAGES.HOT_RELOAD_DEBOUNCE_MS),
        },
        "volumes": {
            str(page_path): page_engine_settings.CONTAINER.PAGE.VOLUME_MAPPING,
            str(page_server_path): {"bind": "/app/server.py", "mode": "ro"},
            str(template_path): {"bind": "/app/template.html", "mode": "ro"},
        },
        "command": command,
        "hostname": container_name,
    }

    # Add port configuration only for port routing mode
    if ports_config:
        container_config["ports"] = ports_config
        container_config["labels"]["external_port"] = str(external_port)
        # Add external port to environment for page server to use
        container_config["environment"]["EXTERNAL_PORT"] = str(external_port)

    # Start container
    container = container_manager.start(**container_config)

    return container, subdomain, url


def stop_page_container(
    container_manager: PageDockerContainerManager,
    page_name: str,
):
    """Stop and remove a page container"""
    container_name = f"{page_engine_settings.CONTAINER.PAGE.PREFIX_NAME}-{page_name.replace(' ', '-')}"
    container_manager.stop(container_name)


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
