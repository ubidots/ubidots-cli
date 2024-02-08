from datetime import datetime

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from cli.commons.models import BaseYAMLDumpModel
from cli.commons.validators import is_valid_object_id
from cli.functions.enums import FunctionLanguageEnum
from cli.functions.enums import FunctionNodejsRuntimeLayerTypeEnum
from cli.functions.enums import FunctionPythonRuntimeLayerTypeEnum
from cli.settings import settings


class FunctionProjectInfo(BaseModel):
    name: str = settings.FUNCTIONS.DEFAULT_PROJECT_NAME
    language: FunctionLanguageEnum
    runtime: FunctionPythonRuntimeLayerTypeEnum | FunctionNodejsRuntimeLayerTypeEnum
    main_file: str = ""
    created: datetime = Field(default_factory=datetime.now)

    @model_validator(mode="after")
    def set_main_file_based_on_language(self):
        language_value = self.language.value
        self.main_file = FunctionLanguageEnum(language_value).main_file
        return self


class FunctionInfo(BaseModel):
    id: str | None = None

    @field_validator("id")
    @classmethod
    def validate_id(cls, value):
        if isinstance(value, str) and not is_valid_object_id(value):
            error_message = "Input is not a valid object id"
            ValueError(error_message)
        return value


class FunctionProjectMetadata(BaseYAMLDumpModel):
    project: FunctionProjectInfo
    function: FunctionInfo | None = None
