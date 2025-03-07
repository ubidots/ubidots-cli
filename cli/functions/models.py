from pydantic import BaseModel

from cli.commons.models import BaseYAMLDumpModel
from cli.functions.engines.enums import FunctionEngineTypeEnum
from cli.functions.engines.settings import engine_settings
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.enums import FunctionMethodEnum
from cli.functions.enums import FunctionRuntimeLayerTypeEnum


class FunctionGlobalsModel(BaseModel):
    engine: FunctionEngineTypeEnum = engine_settings.CONTAINER.DEFAULT_ENGINE
    label: str = ""


class FunctionServerlessModel(BaseModel):
    runtime: FunctionRuntimeLayerTypeEnum
    params: str
    authToken: str
    isRawFunction: bool
    timeout: int


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
    runtime: FunctionRuntimeLayerTypeEnum


class FunctionModel(BaseModel):
    id: str
    serverless: FunctionServerlessModel
    triggers: FunctionTriggersModel
    label: str


class FunctionProjectMetadata(BaseYAMLDumpModel):
    globals: FunctionGlobalsModel
    project: FunctionProjectModel
    function: FunctionModel
