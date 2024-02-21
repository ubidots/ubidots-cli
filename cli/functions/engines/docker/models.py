from docker.models.containers import Container
from pydantic import Field
from pydantic import model_validator

from cli.functions.engines.enums import ContainerStatusEnum
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.models import ContainerStatusBaseModel
from cli.functions.engines.models import ContainerStatusListBaseModel
from cli.settings import settings


class DockerContainerStatusBaseModel(ContainerStatusBaseModel):
    ports: list[dict] = Field(exclude=True)

    @model_validator(mode="after")
    def get_ip_and_port_for_bind(self):
        self.bind = (
            f"{self.ports[0]['HostIp']}:{self.ports[0]['HostPort']}"
            if self.ports
            else ""
        )
        return self


class DockerContainerStatusListModel(ContainerStatusListBaseModel):
    @classmethod
    def from_containers_list(
        cls, containers: list[Container]
    ) -> "DockerContainerStatusListModel":
        container_models = []
        for container in containers:
            container_model = DockerContainerStatusBaseModel(
                engine=FunctionEngineTypeEnum.DOCKER.value,
                label=container.labels.get(
                    settings.FUNCTIONS.DOCKER_CONFIG.CONTAINER_KEY, ""
                ),
                ports=container.ports.get(
                    settings.FUNCTIONS.DOCKER_CONFIG.CONTAINER_PORT, []
                ),
                status=ContainerStatusEnum(container.status).value,
                raw=True,
            )
            container_models.append(container_model)
        return cls(containers=container_models)
