from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator

from cli.functions.engines.enums import ContainerStatusEnum
from cli.functions.engines.enums import FunctionEngineTypeEnum


class ContainerStatusBaseModel(BaseModel):
    engine: FunctionEngineTypeEnum | str = ""
    label: str = ""
    bind: str = ""
    status: ContainerStatusEnum | str = ""
    raw: bool = Field(default=True)


class ContainerStatusListBaseModel(BaseModel):
    containers: list[ContainerStatusBaseModel] = []

    @field_validator("containers")
    @classmethod
    def validate_containers(cls, values):
        if not values:
            return [
                dict.fromkeys(
                    ContainerStatusBaseModel.model_json_schema()["properties"].keys(),
                    "",
                )
            ]
        return [value.dict() for value in values]
