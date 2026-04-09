import logging
from contextlib import suppress
from dataclasses import dataclass
from dataclasses import field

from docker.errors import APIError
from cli.commons.engines.docker.container import BaseDockerContainerManager
from cli.commons.exceptions import ContainerNotFoundError
from cli.pages.engines.enums import PageEngineTypeEnum

logger = logging.getLogger(__name__)

@dataclass
class PageDockerContainerManager(BaseDockerContainerManager):
    engine: PageEngineTypeEnum = field(default=PageEngineTypeEnum.DOCKER)

    def stop(self, label: str) -> None:
        """Stop container gracefully (suppress errors)."""
        try:
            container = self.get(label=label)
            if container.status == "running":
                container.stop()
        except ContainerNotFoundError:
            pass # Container already gone
        except APIError as e:
            logger.debug("Failed to stop container %s: %s", label, e)
