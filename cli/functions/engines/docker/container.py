from contextlib import suppress
from dataclasses import dataclass
from dataclasses import field

from docker.errors import NotFound

from cli.commons.engines.docker.container import BaseDockerContainerManager
from cli.commons.exceptions import ContainerNotFoundError
from cli.commons.settings import ARGO_CONTAINER_NAME
from cli.functions.engines.docker.models import DockerContainerStatusListModel
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.exceptions import ContainerNotFoundException
from cli.functions.engines.settings import engine_settings


@dataclass
class FunctionDockerContainerManager(BaseDockerContainerManager):
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

    def get(self, label: str, label_key: str | None = None):
        try:
            return super().get(label, label_key)
        except ContainerNotFoundError as err:
            raise ContainerNotFoundException(label) from err

    def list(self, label_filters: dict | None = None):
        if label_filters is None:
            label_filters = {"label": engine_settings.CONTAINER.FRIE.LABEL_KEY}
        return super().list(label_filters)

    def stop(self, label: str) -> None:
        container = self.get(label=label)
        container.stop()
        container.remove()

        if not self.list():
            with suppress(NotFound):
                argo_container = self.client.containers.get(ARGO_CONTAINER_NAME)
                argo_container.stop()
                argo_container.remove()
