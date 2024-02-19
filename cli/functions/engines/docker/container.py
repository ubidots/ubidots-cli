from dataclasses import field

from docker import DockerClient
from docker.errors import APIError
from docker.errors import ContainerError
from docker.models.containers import Container

from cli.functions.engines.abstracts.clients import AbstractContainerManager
from cli.functions.engines.exceptions import ContainerAlreadyRunningException
from cli.functions.engines.exceptions import ContainerExecutionException
from cli.settings import settings


class FunctionDockerContainerManager(AbstractContainerManager):
    client: DockerClient = field(default_factory=DockerClient)

    def list(self, label: str) -> list[Container]:
        return self.client.containers.list(filters={"label": label})

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
