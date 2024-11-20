from contextlib import suppress
from dataclasses import field

from docker import DockerClient
from docker.errors import ContainerError
from docker.errors import NotFound

from cli.functions.engines.abstracts.client import AbstractContainerManager
from cli.functions.engines.docker.models import DockerContainerStatusListModel
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.exceptions import ContainerAlreadyRunningException
from cli.functions.engines.exceptions import ContainerExecutionException
from cli.functions.engines.exceptions import ContainerNotFoundException
from cli.functions.engines.settings import engine_settings


class FunctionDockerContainerManager(AbstractContainerManager):
    client: DockerClient = field(default_factory=DockerClient)
    engine: FunctionEngineTypeEnum = field(default=FunctionEngineTypeEnum.DOCKER)

    def status(
        self,
        container_label_key: str,
        is_raw_label_key: str,
        target_url_label_key: str,
    ):
        containers = self.list()
        status_model = DockerContainerStatusListModel.from_containers_list(
            containers,
            container_label_key,
            is_raw_label_key,
            target_url_label_key,
        )
        return status_model.containers

    def get(
        self,
        label: str,
    ):
        containers = self.list(label)
        container = next(iter(containers), None)
        if container is None:
            raise ContainerNotFoundException(label)
        return container

    def list(
        self,
        label: str = engine_settings.CONTAINER.FRIE.LABEL_KEY,
    ):
        return self.client.containers.list(filters={"label": label})

    def logs(
        self,
        label: str,
        tail: int | str = "all",
        follow: bool = False,
    ):
        container = self.get(label=label)
        return container.logs(tail=tail, follow=follow)

    def start(
        self,
        image_name: str,
        container_name: str,
        network_name: str,
        labels: dict,
        ports: dict[str, tuple[str, int]] | None = None,
        volumes: dict | None = None,
        detach: bool = engine_settings.CONTAINER.IS_DETACH,
        environment: dict | None = None,
        command: str = "",
        hostname: str = "",
    ):
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

        with suppress(NotFound):
            if self.client.containers.get(container_name):
                raise ContainerAlreadyRunningException(container_name=container_name)

        try:
            return self.client.containers.run(**kwargs)
        except ContainerError as error:
            raise ContainerExecutionException from error

    def stop(
        self,
        label: str,
    ):
        container = self.get(label=label)
        container.stop()
        container.remove()

        if not self.list():
            with suppress(NotFound):
                argo_container = self.client.containers.get(
                    engine_settings.CONTAINER.ARGO.NAME
                )
                argo_container.stop()
                argo_container.remove()

    def restart(
        self,
        label: str,
    ):
        container = self.get(label=label)
        container.restart()
