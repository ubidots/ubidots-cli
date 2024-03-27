from docker.models.containers import Container

from cli.functions.engines.enums import ContainerStatusEnum
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.models import ContainerStatusBaseModel
from cli.functions.engines.models import ContainerStatusListBaseModel


class DockerContainerStatusListModel(ContainerStatusListBaseModel):
    @classmethod
    def from_containers_list(
        cls, containers: list[Container], label_key: str
    ) -> "DockerContainerStatusListModel":
        container_models = []
        for container in containers:
            container_model = ContainerStatusBaseModel(
                engine=FunctionEngineTypeEnum.DOCKER,
                label=container.labels.get(label_key, ""),
                status=ContainerStatusEnum(container.status),
                raw=True,
            )
            container_models.append(container_model)
        return cls(containers=container_models)
