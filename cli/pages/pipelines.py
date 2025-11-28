import asyncio
import zipfile
from dataclasses import dataclass
from pathlib import Path

import httpx
import typer

from cli.commons.pipelines import PipelineStep
from cli.commons.utils import build_endpoint
from cli.commons.utils import cleanup_directory
from cli.config.helpers import get_configuration
from cli.functions.exceptions import PermissionDeniedError
from cli.pages.engines.enums import PageEngineTypeEnum
from cli.pages.engines.helpers import build_pages_image_if_needed
from cli.pages.engines.helpers import flask_manager_container_helper
from cli.pages.engines.helpers import get_or_create_pages_network
from cli.pages.engines.helpers import page_container_helper
from cli.pages.engines.helpers import stop_page_container
from cli.pages.engines.manager import PageEngineClientManager
from cli.pages.engines.settings import page_engine_settings
from cli.pages.exceptions import CurrentPlanDoesNotIncludePagesFeature
from cli.pages.exceptions import PageAlreadyExistsInCurrentDirectoryError
from cli.pages.exceptions import PageIsAlreadyRunningError
from cli.pages.exceptions import PageIsAlreadyStoppedError
from cli.pages.exceptions import PageWithNameAlreadyExistsError
from cli.pages.exceptions import TemplateNotFoundError
from cli.pages.helpers import create_and_save_page_manifest
from cli.pages.helpers import extract_port_from_container
from cli.pages.helpers import generate_page_url
from cli.pages.helpers import get_page_container
from cli.pages.helpers import is_container_running
from cli.pages.helpers import read_page_manifest
from cli.pages.helpers import render_index_html
from cli.pages.helpers import render_ubidots_page_index_html
from cli.pages.models import PageModelFactory
from cli.settings import settings


class ReadManifestStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        data["project_metadata"] = read_page_manifest(project_path)
        return data


class ValidateNotRunningFromPageDirectoryStep(PipelineStep):
    def execute(self, data):
        current_dir = Path.cwd()
        manifest_file = current_dir / settings.PAGES.PROJECT_MANIFEST_FILE
        if manifest_file.exists():
            raise PageAlreadyExistsInCurrentDirectoryError()
        return data


class ValidateCurrentPageExistsStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        page_name = data["page_name"]
        manifest_file = project_path / settings.PAGES.PROJECT_MANIFEST_FILE
        if manifest_file.exists() or project_path.exists():
            raise PageWithNameAlreadyExistsError(name=page_name, page_path=project_path)
        return data


class GetActiveConfigStep(PipelineStep):
    def execute(self, data):
        profile = data.get("profile", "")
        data["active_config"] = get_configuration(profile=profile)
        return data


class ValidatePagesAvailabilityPerPlanStep(PipelineStep):
    def execute(self, data):
        active_config = data["active_config"]

        # Build the endpoint using existing utility
        url, headers = build_endpoint(
            route=settings.PAGES.API_ROUTES["base"],
            active_config=active_config,
        )

        try:
            response = httpx.get(url, headers=headers)
            response.raise_for_status()
            # If we get here, the user has access to pages
            return data
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 402:
                raise CurrentPlanDoesNotIncludePagesFeature()
            raise


class ValidateTemplateStep(PipelineStep):
    def execute(self, data):
        page_type = data["page_type"]
        template_file = settings.PAGES.UBIDOTS_PAGE_LAYOUT_ZIP[page_type.value]
        if not template_file.exists():
            raise TemplateNotFoundError(
                page_type=page_type,
                template_file=template_file,
            )
        data["template_file"] = template_file
        return data


class CreateProjectFolderStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]

        try:
            project_path.mkdir(parents=True, exist_ok=False)
        except PermissionError as error:
            raise PermissionDeniedError(error=str(error)) from error
        return data


class ExtractTemplateStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        template_file = data["template_file"]

        with zipfile.ZipFile(template_file, "r") as zip_ref:
            zip_ref.extractall(project_path)

        return data


class ValidateExtractedPageStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        page_type = data["page_type"]

        try:
            # Create page model from project directory
            page_model = PageModelFactory.create_page_model_from_project(
                project_path, page_type
            )

            # Validate the page (structure + files)
            validation_result = page_model.validate_complete(project_path)

            if not validation_result["valid"]:
                # Check if cleanup is enabled and perform cleanup
                if data.get("clean_directory_if_validation_fails", False):
                    cleanup_directory(project_path)

                errors = "; ".join(validation_result["errors"])
                raise ValueError(f"Page validation failed: {errors}")

            # Store validation result in data for potential use by other steps
            data["page_validation"] = validation_result
            return data

        except Exception as e:
            # Check if cleanup is enabled and perform cleanup
            if data.get("clean_directory_if_validation_fails", False):
                cleanup_directory(project_path)

            raise ValueError(f"Page validation failed: {str(e)}")


class SaveManifestStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        page_name = data["page_name"]
        page_type = data["page_type"]

        # Create and save the manifest.yaml file
        metadata = create_and_save_page_manifest(project_path, page_name, page_type)

        # Store metadata in data for potential use by other steps
        data["project_metadata"] = metadata
        return data


class EnsureDockerImageStep(PipelineStep):
    """Ensure the custom Docker image is built for faster page startup"""

    def execute(self, data):
        # This will build the image if it doesn't exist
        # The actual image selection happens later in the start pipeline
        build_pages_image_if_needed()
        return data


class ValidatePageDirectoryStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        manifest_file = project_path / settings.PAGES.PROJECT_MANIFEST_FILE

        if not manifest_file.exists():
            raise FileNotFoundError(
                f"Not in a page directory. Missing "
                f"{settings.PAGES.PROJECT_MANIFEST_FILE} file."
            )

        return data


class ReadPageMetadataStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]

        try:
            data["project_metadata"] = read_page_manifest(project_path)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Missing {settings.PAGES.PROJECT_METADATA_FILE} file. "
                "This directory may not be a properly initialized page."
            )
        except Exception as e:
            raise ValueError(f"Failed to read page metadata: {str(e)}")

        return data


class ValidatePageStructureStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        project_metadata = data["project_metadata"]
        page_type = project_metadata.project.type

        try:
            page_model = PageModelFactory.create_page_model_from_project(
                project_path, page_type
            )

            validation_result = page_model.validate_complete(project_path)

            if not validation_result["valid"]:
                errors = "; ".join(validation_result["errors"])
                raise ValueError(f"Page validation failed: {errors}")

            data["page_validation"] = validation_result
            data["page_model"] = page_model

        except Exception as e:
            raise ValueError(f"Page structure validation failed: {str(e)}")

        return data


# ============================================================================
# Docker Engine Pipeline Steps (for start/stop/restart/logs/status commands)
# ============================================================================


class GetClientStep(PipelineStep):
    """Get the PageEngineClientManager (Docker/Podman client)"""

    def execute(self, data):
        engine_type = page_engine_settings.CONTAINER.DEFAULT_ENGINE
        manager = PageEngineClientManager(engine_type)
        client = manager.get_client()

        data["client"] = client
        return data


class GetContainerManagerStep(PipelineStep):
    """Get the PageDockerContainerManager from the client"""

    def execute(self, data):
        client = data["client"]
        container_manager = client.get_container_manager()

        data["container_manager"] = container_manager
        return data


class GetPageNameStep(PipelineStep):
    """Extract page name from project metadata"""

    def execute(self, data):
        project_metadata = data["project_metadata"]
        page_name = project_metadata.project.name

        data["page_name"] = page_name
        return data


class EnsureFlaskManagerStep(PipelineStep):
    """Ensure Flask manager container is running (start if not)"""

    def execute(self, data):
        # Check routing mode - only start Flask manager for subdomain and path routing
        if settings.PAGES.ROUTING_MODE == "port":
            # For port routing, we don't need the Flask manager
            client = data["client"]
            network = get_or_create_pages_network(client)
            data["network"] = network
            data["flask_manager"] = None
            return data

        client = data["client"]
        container_manager = data["container_manager"]

        # Get or create network
        network = get_or_create_pages_network(client)
        data["network"] = network

        flask_manager_path = settings.PAGES.FLASK_MANAGER_TEMPLATE

        # Start or get existing Flask manager
        flask_manager = flask_manager_container_helper(
            container_manager=container_manager,
            client=client,
            network=network,
            flask_manager_path=flask_manager_path,
        )

        data["flask_manager"] = flask_manager
        return data


class ValidatePageNotRunningStep(PipelineStep):
    """Check if page is already running and exit if it is"""

    def execute(self, data):
        container_manager = data["container_manager"]
        page_name = data["page_name"]

        # Get page container
        container = get_page_container(container_manager, page_name)

        # Check if container is running
        if is_container_running(container):
            # Generate appropriate URL for the error message
            routing_mode = settings.PAGES.ROUTING_MODE
            url = generate_page_url(page_name, routing_mode, container)

            raise PageIsAlreadyRunningError(name=page_name, url=url)

        return data


class StartPageContainerStep(PipelineStep):
    """Start the page container with Docker labels"""

    def execute(self, data):
        container_manager = data["container_manager"]
        network = data["network"]
        page_name = data["page_name"]
        project_path = data["project_path"]

        page_server_path = settings.PAGES.PAGE_SERVER_TEMPLATE

        # Start page container
        container, subdomain, url = page_container_helper(
            container_manager=container_manager,
            network=network,
            page_name=page_name,
            page_path=project_path,
            page_server_path=page_server_path,
            client=data["client"],
        )

        data["page_container"] = container
        data["page_subdomain"] = subdomain
        data["page_url"] = url

        return data


class ValidatePageRunningStep(PipelineStep):
    """Check if page is running before trying to stop it"""

    def execute(self, data):
        container_manager = data["container_manager"]
        page_name = data["page_name"]

        # Get page container
        container = get_page_container(container_manager, page_name)

        # Check if container is NOT running
        if not is_container_running(container):
            raise PageIsAlreadyStoppedError(name=page_name)

        return data


class StopPageContainerStep(PipelineStep):
    """Stop and remove the page container"""

    def execute(self, data):
        container_manager = data["container_manager"]
        page_name = data["page_name"]

        stop_page_container(
            container_manager=container_manager,
            page_name=page_name,
        )

        return data


class RestartPageContainerStep(PipelineStep):
    """Restart the page container"""

    def execute(self, data):
        container_manager = data["container_manager"]
        page_name = data["page_name"]

        container_name = (
            f"{page_engine_settings.CONTAINER.PAGE.PREFIX_NAME}-{page_name}"
        )
        container_manager.restart(container_name)

        return data


@dataclass
class GetPageLogsStep(PipelineStep):
    """Get logs from the page container"""

    tail: int | str
    follow: bool

    def execute(self, data):
        container_manager = data["container_manager"]
        page_name = data["page_name"]

        container_name = (
            f"{page_engine_settings.CONTAINER.PAGE.PREFIX_NAME}-{page_name}"
        )
        logs = container_manager.logs(
            name=container_name,
            tail=self.tail,
            follow=self.follow,
        )

        data["logs"] = logs
        return data


class GetPageStatusStep(PipelineStep):
    """Get the current status of the page container"""

    def execute(self, data):
        container_manager = data["container_manager"]
        page_name = data["page_name"]

        # Get page container
        container = get_page_container(container_manager, page_name)

        # Determine status
        if container is None:
            status = "stopped"
            url = ""
        elif is_container_running(container):
            status = "running"
            routing_mode = settings.PAGES.ROUTING_MODE
            url = generate_page_url(page_name, routing_mode, container)
        else:
            status = "stopped"
            url = ""

        data["page_status"] = status
        data["page_url"] = url

        return data


class GetPageStatusTableStep(PipelineStep):
    """Get the current page status formatted for table display like functions module"""

    def execute(self, data):
        container_manager = data["container_manager"]
        page_name = data["page_name"]

        # Get page container
        container = get_page_container(container_manager, page_name)

        # Determine status
        if container is None:
            status = "stopped"
            url = "-"
        elif is_container_running(container):
            status = "running"
            routing_mode = settings.PAGES.ROUTING_MODE
            url = generate_page_url(page_name, routing_mode, container)
        else:
            status = "stopped"
            url = "-"

        # Format as list of dictionaries for table display (like functions module)
        status_info = [
            {
                "name": page_name,
                "status": status,
                "url": url,
            }
        ]

        data["status"] = status_info
        return data


class PrintPageStatusStep(PipelineStep):
    """Print the page status information"""

    def execute(self, data):
        page_name = data["page_name"]
        status = data["page_status"]
        url = data.get("page_url", "")

        print(f"📄 Page: {page_name}")
        print(f"🔄 Status: {status}")

        if status == "running" and url:
            print(f"🌐 URL: {url}")

        return data


class ListAllPagesStep(PipelineStep):
    """List all page containers (running and stopped) using Docker labels only"""

    def execute(self, data):
        container_manager = data["container_manager"]

        # Get all containers with page labels (both running and stopped)
        try:
            # Get all containers (including stopped ones) with the page label
            containers = container_manager.list(
                filters={"label": "ubidots_cli_page=true"},
                all=True,  # Include stopped containers
            )

            pages_info = []
            for container in containers:
                # Extract page name from container name
                container_name = container.name
                prefix = page_engine_settings.CONTAINER.PAGE.PREFIX_NAME + "-"
                if container_name.startswith(prefix):
                    page_name = container_name[len(prefix) :]

                    # Get status
                    status = "running" if container.status == "running" else "stopped"

                    # Generate URL if running
                    url = ""
                    if status == "running":
                        routing_mode = settings.PAGES.ROUTING_MODE
                        url = generate_page_url(page_name, routing_mode, container)

                    pages_info.append(
                        {
                            "name": page_name,
                            "status": status,
                            "url": url if url else "-",
                        }
                    )

            # Sort by name for consistent output
            pages_info.sort(key=lambda x: x["name"])
            data["pages_info"] = pages_info

        except Exception as e:
            print(f"Error listing pages: {e}")
            data["pages_info"] = []

        return data


class PrintPagesListStep(PipelineStep):
    """Print the list of all pages using Rich table format like functions module"""

    def execute(self, data):
        from cli.commons.styles import print_colored_table

        pages_info = data.get("pages_info", [])

        if not pages_info:
            print("No pages found.")
            return data

        # Use Rich table formatting like functions module
        print_colored_table(results=pages_info, column_order=["name", "status", "url"])

        return data


@dataclass
class PrintColoredTableStep(PipelineStep):
    """Print data in colored table format like functions module"""

    key: str = ""

    def execute(self, data):
        from cli.commons.styles import print_colored_table

        if self.key and self.key in data:
            results = data[self.key]
            print_colored_table(results=results, column_order=["name", "status", "url"])
        return data


class PrintPageUrlStep(PipelineStep):
    """Print the page URL to the console"""

    def execute(self, data):
        page_url = data.get("page_url", "")
        routing_mode = settings.PAGES.ROUTING_MODE

        if page_url:
            if routing_mode == "subdomain":
                typer.echo(f"\n🌐 Page URL (subdomain): {page_url}\n")
            elif routing_mode == "port":
                typer.echo(f"\n🌐 Page URL (direct port): {page_url}\n")
            elif routing_mode == "path":
                typer.echo(f"\n🌐 Page URL (path-based): {page_url}\n")
            else:
                typer.echo(f"\n🌐 Page URL: {page_url}\n")
        return data
