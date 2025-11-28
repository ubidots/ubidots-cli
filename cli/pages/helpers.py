from datetime import datetime
from pathlib import Path
from typing import Any
from typing import Dict

import yaml
from jinja2 import Template

from cli.pages.models import PageModel
from cli.pages.models import PageProjectMetadata
from cli.pages.models import PageProjectModel
from cli.pages.models import PageTypeEnum
from cli.settings import settings


def read_page_manifest(project_path: Path) -> PageProjectMetadata:
    metadata_file = project_path / settings.PAGES.PROJECT_METADATA_FILE

    if not metadata_file.exists():
        error_message = (
            f"'{metadata_file}' not found. Are you in the correct project " "directory?"
        )
        raise FileNotFoundError(error_message)

    with open(metadata_file, "r") as file:
        metadata_data = yaml.safe_load(file)

    obj = PageProjectMetadata(**metadata_data)
    return obj


def save_page_manifest(project_path: Path, metadata: PageProjectMetadata) -> None:
    """Save PageProjectMetadata to manifest.yaml file."""
    manifest_file = project_path / settings.PAGES.PROJECT_METADATA_FILE

    # Save as YAML using the model's serialization method
    with open(manifest_file, "w") as file:
        yaml.dump(metadata.to_yaml_serializable_format(), file)


def create_and_save_page_manifest(
    project_path: Path, page_name: str, page_type: PageTypeEnum, page_id: str = ""
) -> PageProjectMetadata:
    """Create PageProjectMetadata and save it to manifest.yaml file."""
    # Create project model
    project_model = PageProjectModel(
        name=page_name,
        label=page_name,
        createdAt=datetime.now().isoformat(),
        type=page_type,
    )

    # Create page model
    page_model = PageModel(id=page_id, label=page_name, name=page_name)

    # Create metadata
    metadata = PageProjectMetadata(project=project_model, page=page_model)

    # Save the manifest.yaml file
    save_page_manifest(project_path, metadata)

    return metadata


class _TemplateLibrary:
    """Helper class to make dictionary compatible with template expectations."""

    def __init__(self, data: Dict[str, Any]):
        self.items = list(data.items())


def render_ubidots_page_index_html(
    page: Dict[str, Any],
    page_type: PageTypeEnum,
    BASE_URL: str,
    HTML_CANVAS_LIBRARY_URL: str,
    REACT_URL: str,
    REACT_DOM_URL: str,
    BABEL_STANDALONE_URL: str,
    VULCANUI_JS_URL: str,
    VULCANUI_CSS_URL: str,
) -> str:
    # Load the template
    template_path = settings.PAGES.UBIDOTS_PAGE_HTML[page_type.value]
    template_content = template_path.read_text(encoding="utf-8")
    template = Template(template_content)

    # Convert library dictionaries to template-compatible format
    def _convert_libraries(libraries):
        return [_TemplateLibrary(lib) for lib in libraries]

    # Prepare page data with converted libraries
    template_page = page.copy()
    template_page["js_libraries"] = _convert_libraries(page.get("js_libraries", []))
    template_page["css_libraries"] = _convert_libraries(page.get("css_libraries", []))
    template_page["link_libraries"] = _convert_libraries(page.get("link_libraries", []))
    template_page["js_thirdparty_libraries"] = _convert_libraries(
        page.get("js_thirdparty_libraries", [])
    )
    template_page["css_thirdparty_libraries"] = _convert_libraries(
        page.get("css_thirdparty_libraries", [])
    )
    template_page["link_thirdparty_libraries"] = _convert_libraries(
        page.get("link_thirdparty_libraries", [])
    )

    # Prepare template context with all mandatory parameters
    context = {
        "page": template_page,
        "BASE_URL": BASE_URL,
        "HTML_CANVAS_LIBRARY_URL": HTML_CANVAS_LIBRARY_URL,
        "REACT_URL": REACT_URL,
        "REACT_DOM_URL": REACT_DOM_URL,
        "BABEL_STANDALONE_URL": BABEL_STANDALONE_URL,
        "VULCANUI_JS_URL": VULCANUI_JS_URL,
        "VULCANUI_CSS_URL": VULCANUI_CSS_URL,
    }

    # Render and return the template
    return template.render(context)


def render_index_html(ubidots_page_html: str, page_type: PageTypeEnum) -> str:

    template_path = settings.PAGES.INDEX_HTML[page_type.value]

    template_file = Path(template_path)
    if not template_file.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")

    template_content = template_file.read_text(encoding="utf-8")
    template = Template(template_content)

    context = {"ubidots_page_html": ubidots_page_html}

    return template.render(context)


# ============================================================================
# Container Validation Utilities
# ============================================================================


def get_page_container(container_manager, page_name):
    """Get page container by name, return None if not found"""
    from cli.pages.engines.settings import page_engine_settings

    container_name = f"{page_engine_settings.CONTAINER.PAGE.PREFIX_NAME}-{page_name}"
    try:
        return container_manager.get(container_name)
    except Exception:
        return None


def is_container_running(container):
    """Check if container exists and is running"""
    return container is not None and container.status == "running"


def extract_port_from_container(container):
    """Extract external port from container port mappings"""
    if not hasattr(container, "ports") or not container.ports:
        return None

    for port_mapping in container.ports.values():
        if port_mapping:
            for mapping in port_mapping:
                if mapping.get("HostPort"):
                    return mapping["HostPort"]
    return None


def generate_page_url(page_name, routing_mode, container=None):
    """Generate page URL based on routing mode"""
    from cli.pages.engines.settings import page_engine_settings

    if routing_mode == "subdomain":
        flask_port = page_engine_settings.CONTAINER.FLASK_MANAGER.EXTERNAL_PORT
        return f"http://{page_name}.localhost:{flask_port}/"

    if routing_mode == "path":
        flask_port = page_engine_settings.CONTAINER.FLASK_MANAGER.EXTERNAL_PORT
        return f"http://localhost:{flask_port}/{page_name}"

    if routing_mode == "port":
        external_port = extract_port_from_container(container)
        port = external_port if external_port else "8090"
        return f"http://localhost:{port}/"

    return ""
