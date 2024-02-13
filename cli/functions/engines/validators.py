from abc import ABC
from abc import abstractmethod
from typing import Any

from cli.functions.engines.exceptions import EngineNotInstalledException
from cli.functions.engines.exceptions import ImageNotAvailableLocallyException


class AbstractEngineValidator(ABC):
    def __init__(self, client: Any):
        self.client = client

    @abstractmethod
    def validate_engine_installed(self):
        raise NotImplementedError

    @abstractmethod
    def validate_image_available_locally(self, image_name: str):
        raise NotImplementedError

    def handle_engine_exception(self, error: Exception, engine: str) -> None:
        raise EngineNotInstalledException(engine) from error

    def handle_image_exception(
        self, error: Exception, engine: str, image_name: str
    ) -> None:
        raise ImageNotAvailableLocallyException(engine, image_name) from error
