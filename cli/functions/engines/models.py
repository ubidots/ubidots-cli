from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator

from cli.functions.engines.enums import ContainerStatusEnum
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.enums import TargetTypeEnum
from cli.functions.enums import FunctionMethodEnum


class ContainerStatusBaseModel(BaseModel):
    engine: FunctionEngineTypeEnum
    label: str
    status: ContainerStatusEnum
    raw: bool = Field(default=True)
    url: str = ""


class ArgoAdapterMiddlewareBaseModel(BaseModel):
    type: str = "allowed_methods"
    methods: list[FunctionMethodEnum] = [
        FunctionMethodEnum.GET,
        FunctionMethodEnum.POST,
    ]


class ArgoAdapterTargetBaseModel(BaseModel):
    type: TargetTypeEnum
    url: str
    auth_token: str = ""


class ArgoAdapterBaseModel(BaseModel):
    label: str
    path: str
    is_strict: bool = Field(default=True)
    middlewares: list[ArgoAdapterMiddlewareBaseModel] = Field(
        default=[ArgoAdapterMiddlewareBaseModel()]
    )
    target: ArgoAdapterTargetBaseModel


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
