from dataclasses import dataclass

import typer

from cli.commons.pipelines import PipelineStep
from cli.commons.styles import print_colored_table
from cli.pages.engines.helpers import build_pages_image_if_needed
from cli.pages.engines.helpers import flask_manager_container_helper
from cli.pages.engines.helpers import get_or_create_pages_network
from cli.pages.engines.helpers import page_container_helper
from cli.pages.engines.helpers import stop_page_container
from cli.pages.engines.manager import PageEngineClientManager
from cli.pages.engines.settings import page_engine_settings
from cli.pages.exceptions import PageIsAlreadyRunningError
from cli.pages.exceptions import PageIsAlreadyStoppedError
from cli.pages.helpers import generate_page_url
from cli.pages.helpers import get_page_container
from cli.pages.helpers import is_container_running
from cli.pages.helpers import read_page_manifest
from cli.pages.models import PageModelFactory
from cli.settings import settings


class EnsureDockerImageStep(PipelineStep):
    def execute(self, data):
        build_pages_image_if_needed()
        return data


class ValidatePageDirectoryStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]
        manifest_file = project_path / settings.PAGES.PROJECT_MANIFEST_FILE

        if not manifest_file.exists():
            msg = (
                "Not in a page directory. Run this command inside a page project "
                "or use 'dev add' to create one."
            )
            raise FileNotFoundError(msg)

        return data


class ReadPageMetadataStep(PipelineStep):
    def execute(self, data):
        project_path = data["project_path"]

        try:
            data["project_metadata"] = read_page_manifest(project_path)
        except FileNotFoundError as err:
            msg = (
                "Not in a page directory. Run this command inside a page project "
                "or use 'dev add' to create one."
            )
            raise FileNotFoundError(msg) from err
        except Exception as e:
            msg = f"Failed to read page metadata: {e!s}"
            raise ValueError(msg) from e

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
                msg = f"Page validation failed: {errors}"
                raise ValueError(msg)

            data["page_validation"] = validation_result
            data["page_model"] = page_model

        except Exception as e:
            msg = f"Page structure validation failed: {e!s}"
            raise ValueError(msg) from e

        return data


class GetClientStep(PipelineStep):
    def execute(self, data):
        engine_type = page_engine_settings.CONTAINER.DEFAULT_ENGINE
        manager = PageEngineClientManager(engine_type)
        client = manager.get_client()

        data["client"] = client
        return data


class GetContainerManagerStep(PipelineStep):
    def execute(self, data):
        client = data["client"]
        container_manager = client.get_container_manager()

        data["container_manager"] = container_manager
        return data


class GetPageNameStep(PipelineStep):
    def execute(self, data):
        project_metadata = data["project_metadata"]
        page_name = project_metadata.project.name

        data["page_name"] = page_name
        return data


class EnsureFlaskManagerStep(PipelineStep):
    def execute(self, data):
        if settings.PAGES.ROUTING_MODE == "port":
            client = data["client"]
            network = get_or_create_pages_network(client)
            data["network"] = network
            data["flask_manager"] = None
            return data

        client = data["client"]
        container_manager = data["container_manager"]

        network = get_or_create_pages_network(client)
        data["network"] = network

        flask_manager_path = settings.PAGES.FLASK_MANAGER_TEMPLATE

        flask_manager = flask_manager_container_helper(
            container_manager=container_manager,
            client=client,
            network=network,
            flask_manager_path=flask_manager_path,
        )

        data["flask_manager"] = flask_manager
        return data


class ValidatePageNotRunningStep(PipelineStep):
    def execute(self, data):
        container_manager = data["container_manager"]
        page_name = data["page_name"]

        container = get_page_container(container_manager, page_name)

        if is_container_running(container):
            routing_mode = settings.PAGES.ROUTING_MODE
            url = generate_page_url(page_name, routing_mode, container)

            raise PageIsAlreadyRunningError(name=page_name, url=url)

        return data


class StartPageContainerStep(PipelineStep):
    def execute(self, data):
        container_manager = data["container_manager"]
        network = data["network"]
        page_name = data["page_name"]
        project_path = data["project_path"]

        page_server_path = settings.PAGES.PAGE_SERVER_TEMPLATE

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
    def execute(self, data):
        container_manager = data["container_manager"]
        page_name = data["page_name"]

        container = get_page_container(container_manager, page_name)

        if not is_container_running(container):
            raise PageIsAlreadyStoppedError(name=page_name)

        return data


class StopPageContainerStep(PipelineStep):
    def execute(self, data):
        container_manager = data["container_manager"]
        page_name = data["page_name"]

        stop_page_container(
            container_manager=container_manager,
            page_name=page_name,
        )

        return data


class RestartPageContainerStep(PipelineStep):
    def execute(self, data):
        container_manager = data["container_manager"]
        page_name = data["page_name"]

        container_name = (
            f"{page_engine_settings.CONTAINER.PAGE.PREFIX_NAME}-{page_name.replace(' ', '-')}"
        )
        container_manager.restart(container_name)

        return data


@dataclass
class GetPageLogsStep(PipelineStep):
    tail: int | str
    follow: bool

    def execute(self, data):
        container_manager = data["container_manager"]
        page_name = data["page_name"]

        container_name = (
            f"{page_engine_settings.CONTAINER.PAGE.PREFIX_NAME}-{page_name.replace(' ', '-')}"
        )
        logs = container_manager.logs(
            name=container_name,
            tail=self.tail,
            follow=self.follow,
        )

        data["logs"] = logs
        return data


class GetPageStatusStep(PipelineStep):
    def execute(self, data):
        container_manager = data["container_manager"]
        page_name = data["page_name"]

        container = get_page_container(container_manager, page_name)

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
    def execute(self, data):
        container_manager = data["container_manager"]
        page_name = data["page_name"]

        container = get_page_container(container_manager, page_name)

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
    def execute(self, data):
        container_manager = data["container_manager"]

        try:
            containers = container_manager.list(
                filters={"label": "ubidots_cli_page=true"},
                all=True,
            )

            pages_info = []
            for container in containers:
                container_name = container.name
                prefix = page_engine_settings.CONTAINER.PAGE.PREFIX_NAME + "-"
                if container_name.startswith(prefix):
                    page_name = container_name[len(prefix) :]

                    status = "running" if container.status == "running" else "stopped"

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

            pages_info.sort(key=lambda x: x["name"])
            data["pages_info"] = pages_info

        except Exception as e:
            print(f"Error listing pages: {e}")
            data["pages_info"] = []

        return data


class PrintPagesListStep(PipelineStep):
    def execute(self, data):
        pages_info = data.get("pages_info", [])

        if not pages_info:
            print("No pages found.")
            return data

        print_colored_table(results=pages_info, column_order=["name", "status", "url"])

        return data


@dataclass
class PrintColoredTableStep(PipelineStep):
    key: str = ""

    def execute(self, data):
        if self.key and self.key in data:
            results = data[self.key]
            print_colored_table(results=results, column_order=["name", "status", "url"])
        return data


class PrintPageUrlStep(PipelineStep):
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


@dataclass
class PrintkeyStep(PipelineStep):
    key: str = ""

    def execute(self, data):
        if self.key and self.key in data:
            typer.echo(data[self.key])
        return data
