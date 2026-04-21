from abc import ABC
from abc import abstractmethod
from contextlib import suppress
from dataclasses import dataclass

from docker import DockerClient
from docker.errors import ContainerError
from docker.errors import NotFound

from cli.commons.exceptions import ContainerAlreadyRunningException
from cli.commons.exceptions import ContainerExecutionException
from cli.commons.exceptions import ContainerNotFoundError


@dataclass
class BaseDockerContainerManager(ABC):
    client: DockerClient

    def get(self, label: str):
        """Label-based container lookup. Raises ContainerNotFoundError if not found."""
        containers = self.list({"label": label})
        container = next(iter(containers), None)
        if container is None:
            raise ContainerNotFoundError(label)
        return container

    def list(self, label_filters: dict | None = None):
        """Label-based container filtering."""
        return self.client.containers.list(filters=label_filters or {})

    def start(
        self,
        image_name: str,
        container_name: str,
        network_name: str,
        labels: dict,
        ports: dict | None = None,
        volumes: dict | None = None,
        detach: bool = True,
        environment: dict | None = None,
        command: str = "",
        hostname: str = "",
        user: str = "",
    ):
        """Start a container. Removes any stopped container with the same name first."""
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
        if user:
            kwargs["user"] = user

        with suppress(NotFound):
            existing = self.client.containers.get(container_name)
            if existing.status == "running":
                raise ContainerAlreadyRunningException(container_name=container_name)
            existing.remove()

        try:
            return self.client.containers.run(**kwargs)
        except ContainerError as error:
            raise ContainerExecutionException from error

    @abstractmethod
    def stop(self, label: str) -> None: ...

    def logs(self, label: str, tail: int | str = "all", follow: bool = False):
        """Get logs for a container identified by label."""
        container = self.get(label=label)
        return container.logs(tail=tail, follow=follow)

    def restart(self, label: str) -> None:
        """Restart a container identified by label."""
        container = self.get(label=label)
        container.restart()
