from enum import Enum
from typing import Any

from pydantic import BaseModel


class BaseYAMLDumpModel(BaseModel):
    def to_yaml_serializable_format(self) -> Any:
        data = self.model_dump()

        def _convert_enums_to_values(obj: Any) -> Any:
            match obj:
                case Enum():
                    return obj.value
                case dict():
                    return {
                        key: _convert_enums_to_values(value)
                        for key, value in obj.items()
                    }
                case list():
                    return [_convert_enums_to_values(item) for item in obj]
                case _:
                    return obj

        return _convert_enums_to_values(data)
