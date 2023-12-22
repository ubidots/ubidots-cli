from datetime import datetime
from typing import Any

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator

from cli import settings
from cli.functions.enums import FunctionLanguageEnum


class FunctionProjectInfo(BaseModel):
    name: str = settings.UBIDOTS_FUNCTIONS_DEFAULT_PROJECT_NAME
    language: FunctionLanguageEnum
    main_file: str = ""
    created: datetime = Field(default_factory=datetime.now)

    @model_validator(mode="before")
    def set_main_file_based_on_language(cls, values: dict[str, Any]) -> dict[str, Any]:
        language_str = values.get("language")
        try:
            values["main_file"] = FunctionLanguageEnum(language_str).main_file
        except ValueError as error:
            error_message = (
                f"'{language_str}' is not a valid language. "
                f"Choose from: {[lang.value for lang in FunctionLanguageEnum]}"
            )
            raise ValueError(error_message) from error
        return values


class FunctionInfo(BaseModel):
    id: str | None = None


class FunctionProjectMetadata(BaseModel):
    project: FunctionProjectInfo
    function: FunctionInfo | None = None

    def for_yaml_dump(self):
        data = self.model_dump()
        if isinstance(self.project.language, FunctionLanguageEnum):
            data["project"]["language"] = self.project.language.value
        return data
