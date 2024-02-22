from collections.abc import Generator
from dataclasses import field
from typing import Any

from docker import DockerClient
from docker.errors import APIError
from docker.errors import ContainerError
from docker.models.containers import Container

from cli.functions.engines.abstracts.clients import AbstractContainerManager
from cli.functions.engines.docker.models import DockerContainerStatusListModel
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.exceptions import ContainerAlreadyRunningException
from cli.functions.engines.exceptions import ContainerExecutionException
from cli.functions.engines.exceptions import ContainerNotFoundException
from cli.settings import settings


class FunctionDockerContainerManager(AbstractContainerManager):
    client: DockerClient = field(default_factory=DockerClient)
    engine: FunctionEngineTypeEnum = field(
        default_factory=FunctionEngineTypeEnum.DOCKER
    )

    def status(self) -> list[dict[str, Any]]:
        containers = self.list()
        status_model = DockerContainerStatusListModel.from_containers_list(containers)
        return status_model.containers

    def list(
        self, label: str = settings.FUNCTIONS.DOCKER_CONFIG.CONTAINER_KEY
    ) -> list[Container]:
        return self.client.containers.list(filters={"label": label})

    def logs(
        self, label: str, tail: int | str = "all", follow: bool = False
    ) -> Generator | str:
        label_pair = f"{settings.FUNCTIONS.DOCKER_CONFIG.CONTAINER_KEY}={label}"
        containers = self.list(label=label_pair)
        container = next(iter(containers), None)
        if container is None:
            raise ContainerNotFoundException(label=label_pair)

        return container.logs(tail=tail, follow=follow)

    def start(
        self, image_name: str, labels: dict, volumes: dict, ports: dict, detach: bool
    ) -> Container:
        try:
            return self.client.containers.run(
                image=image_name,
                labels=labels,
                volumes=volumes,
                ports=ports,
                detach=detach,
            )
        except APIError as error:
            host, port = ports[f"{settings.FUNCTIONS.DOCKER_CONFIG.CONTAINER_PORT}"]
            raise ContainerAlreadyRunningException(host=host, port=port) from error
        except ContainerError as error:
            raise ContainerExecutionException from error

    def stop(self, label: str) -> None:
        label_pair = f"{settings.FUNCTIONS.DOCKER_CONFIG.CONTAINER_KEY}={label}"
        containers = self.list(label=label_pair)
        container = next(iter(containers), None)
        if container is None:
            raise ContainerNotFoundException(label=label_pair)

        container.stop()
        container.remove()
