from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from typing import Any

from cli.functions.engines.exceptions import EngineNotInstalledException
from cli.functions.engines.exceptions import ImageNotAvailableLocallyException


@dataclass
class AbstractEngineValidator(ABC):
    client: Any

    @abstractmethod
    def validate_engine_installed(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def validate_image_available_locally(self, image_name: str) -> None:
        raise NotImplementedError

    @staticmethod
    def _engine_not_installed(engine: str) -> Exception:
        return EngineNotInstalledException(engine)

    @staticmethod
    def _image_not_available_locally(engine: str, image_name: str) -> Exception:
        return ImageNotAvailableLocallyException(engine, image_name)

    @staticmethod
    def raise_exception(error_type: str, engine: str, image_name: str) -> None:
        error_map = {
            "engine_not_installed": AbstractEngineValidator._engine_not_installed,
            "image_not_available_locally": AbstractEngineValidator._image_not_available_locally,
        }

        error_function = error_map.get(error_type)
        if error_function:
            raise error_function(engine, image_name)
        error_message = f"Unknown error type: {error_type}"
        raise ValueError(error_message)
