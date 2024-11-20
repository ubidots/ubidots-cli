from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator

from cli.functions.engines.enums import ArgoMethodEnum
from cli.functions.engines.enums import ContainerStatusEnum
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.enums import MiddlewareTypeEnum
from cli.functions.engines.enums import TargetTypeEnum


class ContainerStatusBaseModel(BaseModel):
    engine: FunctionEngineTypeEnum
    label: str
    status: ContainerStatusEnum
    raw: bool = Field(default=True)
    url: str = ""


class ArgoAdapterMiddlewareAllowedMethodsBaseModel(BaseModel):
    type: MiddlewareTypeEnum = MiddlewareTypeEnum.ALLOWED_METHODS
    methods: list[ArgoMethodEnum] = [
        ArgoMethodEnum.GET,
        ArgoMethodEnum.POST,
    ]


class ArgoAdapterMiddlewareCorsBaseModel(BaseModel):
    type: MiddlewareTypeEnum = MiddlewareTypeEnum.CORS
    allow_origins: list[str] = ["*"]
    allow_methods: list[ArgoMethodEnum] = [
        ArgoMethodEnum.GET,
        ArgoMethodEnum.POST,
        ArgoMethodEnum.OPTIONS,
    ]
    allow_headers: list[str] = [
        "Accept",
        "Accept-Version",
        "Content-Length",
        "Content-MD5",
        "Content-Type",
        "Date",
        "X-Auth-Token",
    ]
    allow_credentials: bool = True
    expose_headers: list[str] = ["X-Auth-Token"]


class ArgoAdapterTargetBaseModel(BaseModel):
    type: TargetTypeEnum
    url: str
    auth_token: str = ""


class ArgoAdapterBaseModel(BaseModel):
    label: str
    path: str
    is_strict: bool = Field(default=True)
    middlewares: list[
        ArgoAdapterMiddlewareAllowedMethodsBaseModel
        | ArgoAdapterMiddlewareCorsBaseModel
    ] = Field(default=[ArgoAdapterMiddlewareAllowedMethodsBaseModel()])
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
