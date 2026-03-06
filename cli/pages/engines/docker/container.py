from contextlib import suppress
from dataclasses import field

from docker import DockerClient
from docker.errors import ContainerError
from docker.errors import NotFound

from cli.pages.engines.abstracts.container import AbstractContainerManager
from cli.pages.engines.enums import PageEngineTypeEnum
from cli.pages.engines.exceptions import ContainerAlreadyRunningException
from cli.pages.engines.exceptions import ContainerExecutionException
from cli.pages.engines.exceptions import ContainerNotFoundException
from cli.pages.engines.settings import page_engine_settings


class PageDockerContainerManager(AbstractContainerManager):
    client: DockerClient = field(default_factory=DockerClient)
    engine: PageEngineTypeEnum = field(default=PageEngineTypeEnum.DOCKER)

    def get(self, name: str):
        """Get container by name"""
        try:
            return self.client.containers.get(name)
        except NotFound as error:
            raise ContainerNotFoundException(name) from error

    def list(self, filters: dict | None = None, all: bool = False):
        """List containers with optional filters"""
        return self.client.containers.list(filters=filters or {}, all=all)

    def start(
        self,
        image_name: str,
        container_name: str,
        network_name: str,
        labels: dict,
        ports: dict[str, tuple[str, int]] | None = None,
        volumes: dict | None = None,
        detach: bool = page_engine_settings.CONTAINER.IS_DETACH,
        environment: dict | None = None,
        command: str = "",
        hostname: str = "",
    ):
        """Start a new container"""
        kwargs = {
            "image": image_name,
            "name": container_name,
            "labels": labels,
            "network": network_name,
            "detach": detach,
        }

        if volumes is not None:
            kwargs["volumes"] = volumes

        if ports is not None:
            kwargs["ports"] = ports

        if command:
            kwargs["command"] = command

        if environment is not None:
            kwargs["environment"] = environment

        if hostname:
            kwargs["hostname"] = hostname

        # Check if container already exists
        with suppress(NotFound):
            existing = self.client.containers.get(container_name)
            if existing.status == "running":
                raise ContainerAlreadyRunningException(container_name=container_name)
            # Remove stopped/exited container
            existing.remove()

        try:
            return self.client.containers.run(**kwargs)
        except ContainerError as error:
            raise ContainerExecutionException from error

    def stop(self, name: str):
        """Stop container (but keep it for status tracking)"""
        try:
            container = self.get(name)
            if container.status == "running":
                container.stop()
        except ContainerNotFoundException:
            pass  # Already stopped/removed

    def logs(self, name: str, tail: int | str = "all", follow: bool = False):
        """Get container logs"""
        container = self.get(name)
        return container.logs(tail=tail, follow=follow)

    def restart(self, name: str):
        """Restart a container"""
        container = self.get(name)
        container.restart()
