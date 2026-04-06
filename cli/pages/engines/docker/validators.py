from dataclasses import dataclass
from dataclasses import field

from docker import DockerClient
from docker.errors import APIError

from cli.pages.engines.enums import PageEngineTypeEnum
from cli.pages.engines.exceptions import EngineNotInstalledException


@dataclass
class PageDockerValidator:
    client: DockerClient = field(default_factory=DockerClient)
    engine: PageEngineTypeEnum = field(default=PageEngineTypeEnum.DOCKER)

    def validate_engine_installed(self) -> None:
        try:
            self.client.ping()
        except APIError as error:
            raise EngineNotInstalledException(engine=self.engine) from error
