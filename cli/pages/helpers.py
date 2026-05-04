import io
import os
import zipfile
from datetime import datetime
from pathlib import Path
from typing import IO
from typing import Any

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
            "Not in a page directory. Run this command inside a page project "
            "or use 'dev add' to create one."
        )
        raise FileNotFoundError(error_message)

    with open(metadata_file) as file:
        metadata_data = yaml.safe_load(file)

    return PageProjectMetadata(**metadata_data)


def save_page_manifest(project_path: Path, metadata: PageProjectMetadata) -> None:
    manifest_file = project_path / settings.PAGES.PROJECT_METADATA_FILE

    # Save as YAML using the model's serialization method
    with open(manifest_file, "w") as file:
        yaml.dump(metadata.to_yaml_serializable_format(), file)


def create_and_save_page_manifest(
    project_path: Path, page_name: str, page_type: PageTypeEnum, page_id: str = ""
) -> PageProjectMetadata:
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


def _add_files_to_zip(
    zipf: zipfile.ZipFile,
    root: str,
    files: list[str],
    project_path: Path,
    exclude_files: list[str],
) -> None:
    for file in files:
        file_path = os.path.join(root, file)
        zip_path = os.path.relpath(file_path, project_path)
        if not any(Path(zip_path).match(pattern) for pattern in exclude_files):
            zipf.write(file_path, zip_path)


def _add_folders_to_zip(
    zipf: zipfile.ZipFile,
    root: str,
    project_path: Path,
    exclude_files: list[str],
) -> None:
    for folder in os.listdir(root):
        folder_path = os.path.join(root, folder)
        if os.path.isdir(folder_path):
            zip_path = os.path.relpath(folder_path, project_path)
            if not any(Path(zip_path).match(pattern) for pattern in exclude_files):
                zipf.write(folder_path, arcname=zip_path)


def compress_page_to_zip(
    project_path: Path, exclude_files: list[str] | None = None
) -> IO[bytes]:
    exclude_files = exclude_files or []
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(project_path):
            _add_files_to_zip(zipf, root, files, project_path, exclude_files)
            _add_folders_to_zip(zipf, root, project_path, exclude_files)
    zip_buffer.seek(0)
    return zip_buffer


class _TemplateLibrary:
    def __init__(self, data: dict[str, Any]):
        self.items = list(data.items())


def render_ubidots_page_index_html(
    page: dict[str, Any],
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


# ============================================================================
# Container Validation Utilities
# ============================================================================


def get_page_container(container_manager, page_name):
    container_name = f"page-{page_name.replace(' ', '-')}"
    try:
        return container_manager.get(container_name)
    except Exception:
        return None


def is_container_running(container):
    return container is not None and container.status == "running"


def extract_port_from_container(container):
    if not hasattr(container, "ports") or not container.ports:
        return None

    for port_mapping in container.ports.values():
        if port_mapping:
            for mapping in port_mapping:
                if mapping.get("HostPort"):
                    return mapping["HostPort"]
    return None


def generate_page_url(page_name, routing_mode, container=None):
    sanitized = page_name.replace(" ", "-")

    if routing_mode == "subdomain":
        flask_port = 8044
        return f"http://{sanitized}.localhost:{flask_port}/"

    if routing_mode == "path":
        flask_port = 8044
        return f"http://localhost:{flask_port}/{sanitized}"

    if routing_mode == "port":
        external_port = extract_port_from_container(container)
        port = external_port if external_port else "8090"
        return f"http://localhost:{port}/"

    return ""
