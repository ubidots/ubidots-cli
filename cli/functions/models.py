import re

from pydantic import BaseModel
from pydantic import field_validator

from cli.commons.models import BaseYAMLDumpModel
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.settings import engine_settings
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.enums import FunctionMethodEnum

_RUNTIME_PATTERN = re.compile(r"^(python\d+\.\d+|nodejs\d+\.x):(lite|base|full)$")


def _validate_runtime(v: str) -> str:
    if not _RUNTIME_PATTERN.match(v):
        msg = (
            f"Invalid runtime format: '{v}'. "
            "Expected format: '<language><version>:<layer>' "
            "(e.g. 'python3.12:lite', 'nodejs20.x:base')."
        )
        raise ValueError(msg)
    return v


class FunctionGlobalsModel(BaseModel):
    engine: FunctionEngineTypeEnum = engine_settings.CONTAINER.DEFAULT_ENGINE
    label: str = ""


class FunctionServerlessModel(BaseModel):
    runtime: str
    params: str
    authToken: str
    isRawFunction: bool
    timeout: int

    @field_validator("runtime")
    @classmethod
    def validate_runtime(cls, v: str) -> str:
        return _validate_runtime(v)


class FunctionTriggersModel(BaseModel):
    httpMethods: list[FunctionMethodEnum]
    httpHasCors: bool
    httpIsSecure: bool
    httpEnabled: bool
    schedulerCron: str
    schedulerEnabled: bool


class FunctionProjectModel(BaseModel):
    createdAt: str
    name: str
    language: FunctionLanguageEnum
    runtime: str

    @field_validator("runtime")
    @classmethod
    def validate_runtime(cls, v: str) -> str:
        return _validate_runtime(v)


class FunctionModel(BaseModel):
    id: str
    serverless: FunctionServerlessModel
    triggers: FunctionTriggersModel
    label: str


class FunctionProjectMetadata(BaseYAMLDumpModel):
    globals: FunctionGlobalsModel
    project: FunctionProjectModel
    function: FunctionModel
