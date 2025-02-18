from typing import Any

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
    params: dict[str, Any]
    authToken: str
    isRawFunction: bool
    timeout: int
    httpHasCors: bool
    httpIsSecure: bool
    httpEnabled: bool
    schedulerCron: str
    schedulerEnabled: bool


class FunctionTriggersModel(BaseModel):
    httpMethods: list[FunctionMethodEnum]


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
    # local_label: str = ""
    # name: str = settings.FUNCTIONS.DEFAULT_PROJECT_NAME
    # language: FunctionLanguageEnum
    # runtime: (
    #    FunctionRuntimeLayerTypeEnum
    #    | FunctionPythonRuntimeLayerTypeEnum
    #    | FunctionNodejsRuntimeLayerTypeEnum
    # ) = FunctionRuntimeLayerTypeEnum.NODEJS_20_LITE
    # main_file: str = ""
    # created: datetime = Field(default_factory=datetime.now)

    # @model_validator(mode="before")
    # def generate_label_based_on_name(cls, values):
    #    if not values.get("local_label"):
    #        suffix = "".join(
    #            secrets.choice(string.ascii_letters + string.digits)
    #            for _ in range(engine_settings.CONTAINER.DEFAULT_LABEL_LENGTH)
    #        )
    #        values["local_label"] = (
    #            f'{engine_settings.CONTAINER.LABEL_PREFIX}_{values["name"]}_{suffix}'
    #        )
    #    return values

    # @model_validator(mode="after")
    # def set_main_file_based_on_language(self):
    #    language_value = self.language
    #    self.main_file = FunctionLanguageEnum(language_value).main_file
    #    return self


# class FunctionInfo(BaseModel):
#    id: str = ""
#    label: str = ""
#    methods: list[FunctionMethodEnum] = [FunctionMethodEnum.GET]
#    token: str = ""
#    is_raw: bool = settings.FUNCTIONS.DEFAULT_IS_RAW
#    has_cors: bool = settings.FUNCTIONS.DEFAULT_HAS_CORS
#    cron: str = settings.FUNCTIONS.DEFAULT_CRON
#    timeout: int = settings.FUNCTIONS.DEFAULT_TIMEOUT_SECONDS
#    payload: str = "{}"
#
#    @field_validator("id")
#    @classmethod
#    def validate_id(cls, value):
#        if value and isinstance(value, str) and not is_valid_object_id(value):
#            error_message = "Input is not a valid object id."
#            ValueError(error_message)
#        return value
#
#    @field_validator("timeout")
#    @classmethod
#    def validate_timeout(cls, value):
#        max_timeout = settings.FUNCTIONS.MAX_TIMEOUT_SECONDS
#        if value > max_timeout:
#            error_message = f"Timeout value must not exceed '{max_timeout}' seconds."
#            raise ValueError(error_message)
#        return value


class FunctionProjectMetadata(BaseYAMLDumpModel):
    globals: FunctionGlobalsModel
    project: FunctionProjectModel
    function: FunctionModel
