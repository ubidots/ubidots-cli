from contextlib import suppress
from dataclasses import dataclass
from dataclasses import field

from cli.commons.engines.docker.container import BaseDockerContainerManager
from cli.commons.exceptions import ContainerNotFoundError
from cli.pages.engines.enums import PageEngineTypeEnum


@dataclass
class PageDockerContainerManager(BaseDockerContainerManager):
    engine: PageEngineTypeEnum = field(default=PageEngineTypeEnum.DOCKER)

    def stop(self, label: str) -> None:
        """Stop container gracefully (suppress errors)."""
        with suppress(ContainerNotFoundError, Exception):
            container = self.get(label=label)
            if container.status == "running":
                container.stop()
