from dataclasses import field

from docker import DockerClient
from docker.errors import APIError
from docker.errors import ContainerError
from docker.models.containers import Container

from cli.functions.engines.abstracts.clients import AbstractContainerManager
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.exceptions import ContainerAlreadyRunningException
from cli.functions.engines.exceptions import ContainerExecutionException
from cli.settings import settings


class FunctionDockerContainerManager(AbstractContainerManager):
    client: DockerClient = field(default_factory=DockerClient)
    engine: FunctionEngineTypeEnum = field(
        default_factory=FunctionEngineTypeEnum.DOCKER
    )

    def status(self) -> list:
        containers = self.list(all=True)
        return [
            {
                "engine": self.engine.value,
                "label": container.labels.get(
                    settings.FUNCTIONS.DOCKER_CONFIG.CONTAINER_KEY
                ),
                "bind": (
                    f"{ports[0]['HostIp']}:{ports[0]['HostPort']}"
                    if (
                        ports := container.ports.get(
                            settings.FUNCTIONS.DOCKER_CONFIG.CONTAINER_PORT
                        )
                    )
                    else ""
                ),
                "status": container.status,
                "raw": True,
            }
            for container in containers
        ]

    def list(self, label: str = "", all: bool = False) -> list[Container]:
        if all:
            label = settings.FUNCTIONS.DOCKER_CONFIG.CONTAINER_KEY

        filters = {"label": label} if label else {}
        return self.client.containers.list(filters=filters)

    def run(
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
