from docker.models.containers import Container

from cli.functions.engines.enums import ContainerStatusEnum
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.models import ContainerStatusBaseModel
from cli.functions.engines.models import ContainerStatusListBaseModel


class DockerContainerStatusListModel(ContainerStatusListBaseModel):
    @classmethod
    def from_containers_list(
        cls,
        containers: list[Container],
        container_label_key: str,
        is_raw_label_key: str,
        target_url_label_key: str,
    ) -> "DockerContainerStatusListModel":
        container_models = []
        for container in containers:
            container_model = ContainerStatusBaseModel(
                engine=FunctionEngineTypeEnum.DOCKER,
                label=container.labels.get(container_label_key, ""),
                status=ContainerStatusEnum(container.status),
                raw=container.labels.get(is_raw_label_key, ""),
                url=container.labels.get(target_url_label_key, ""),
            )
            container_models.append(container_model)
        return cls(containers=container_models)
