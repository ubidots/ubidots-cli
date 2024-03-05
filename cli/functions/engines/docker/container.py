from collections.abc import Generator
from dataclasses import field
from typing import Any

from docker import DockerClient
from docker.errors import APIError
from docker.errors import ContainerError
from docker.models.containers import Container

from cli.functions.engines.abstracts.client import AbstractContainerManager
from cli.functions.engines.docker.models import DockerContainerStatusListModel
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.exceptions import ContainerAlreadyRunningException
from cli.functions.engines.exceptions import ContainerExecutionException
from cli.functions.engines.exceptions import ContainerNotFoundException
from cli.functions.engines.settings import engine_settings


class FunctionDockerContainerManager(AbstractContainerManager):
    client: DockerClient = field(default_factory=DockerClient)
    engine: FunctionEngineTypeEnum = field(
        default_factory=FunctionEngineTypeEnum.DOCKER
    )

    def status(self) -> list[dict[str, Any]]:
        containers = self.list()
        status_model = DockerContainerStatusListModel.from_containers_list(containers)
        return status_model.containers

    def get(self, label: str) -> Container:
        label_pair = f"{engine_settings.CONTAINER.KEY}={label}"
        containers = self.list(label=label_pair)
        container = next(iter(containers), None)
        if container is None:
            raise ContainerNotFoundException(label=label)
        return container

    def list(self, label: str = engine_settings.CONTAINER.KEY) -> list[Container]:
        return self.client.containers.list(filters={"label": label})

    def logs(
        self, label: str, tail: int | str = "all", follow: bool = False
    ) -> Generator | str:
        container = self.get(label=label)
        return container.logs(tail=tail, follow=follow)

    def start(
        self,
        network_name: str,
        image_name: str,
        labels: dict,
        ports: dict[str, tuple[str, int]],
        container_name: str | None = None,
        volumes: dict | None = None,
        detach: bool = engine_settings.CONTAINER.IS_DETACH,
    ) -> Container:
        kwargs = {
            "image": image_name,
            "labels": labels,
            "ports": ports,
            "network": network_name,
            "detach": detach,
        }
        if container_name is not None:
            kwargs["name"] = container_name

        if volumes is not None:
            kwargs["volumes"] = volumes

        try:
            return self.client.containers.run(**kwargs)
        except APIError as error:
            _, port = next(
                (ports[key] for key in engine_settings.CONTAINER.PORTS if key in ports),
                (None, None),
            )
            raise ContainerAlreadyRunningException(port=port) from error
        except ContainerError as error:
            raise ContainerExecutionException from error

    def stop(self, label: str) -> None:
        container = self.get(label=label)
        container.stop()
        container.remove()

    def reload(self, label: str) -> None:
        container = self.get(label=label)
        container.restart()
