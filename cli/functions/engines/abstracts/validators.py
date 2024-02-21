from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any


@dataclass
class AbstractEngineValidator(ABC):
    client: Any
    engine: Enum

    @abstractmethod
    def validate_engine_installed(self) -> None: ...

    @abstractmethod
    def validate_image_available_locally(self, image_name: str) -> None: ...
