from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class AbstractImageDownloader(ABC):
    client: Any

    @abstractmethod
    def pull_image(self, image_name: str) -> None: ...
