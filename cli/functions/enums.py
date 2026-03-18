from enum import Enum
from enum import auto

from cli.compat import StrEnum


class FunctionMainFileExtensionEnum(StrEnum):
    PYTHON_EXTENSION = "py"
    NODEJS_EXTENSION = "js"


class FunctionHandlerFileExtensionEnum(StrEnum):
    PYTHON_EXTENSION = "py"
    NODEJS_EXTENSION = "mjs"


class FunctionLanguageEnum(StrEnum):
    PYTHON = "python"
    NODEJS = "nodejs"

    @property
    def handler_extension(self):
        handler_extension_map = {
            self.PYTHON: FunctionHandlerFileExtensionEnum.PYTHON_EXTENSION,
            self.NODEJS: FunctionHandlerFileExtensionEnum.NODEJS_EXTENSION,
        }
        return handler_extension_map[self]

    @property
    def extension(self):
        extension_map = {
            self.PYTHON: FunctionMainFileExtensionEnum.PYTHON_EXTENSION,
            self.NODEJS: FunctionMainFileExtensionEnum.NODEJS_EXTENSION,
        }
        return extension_map[self]

    @classmethod
    def get_language_by_runtime(cls, runtime: str | StrEnum) -> "FunctionLanguageEnum":
        return cls.PYTHON if runtime.startswith(cls.PYTHON) else cls.NODEJS


class FunctionProjectValidationTypeEnum(Enum):
    MANIFEST_FILE = auto()
    MAIN_FILE_PRESENCE = auto()


class FunctionMethodEnum(StrEnum):
    GET = "GET"
    POST = "POST"

    @classmethod
    def get_default_method(cls) -> str:
        return str(cls.GET.value)

    @classmethod
    def parse_methods_to_enum_list(cls, methods_str: str) -> list["FunctionMethodEnum"]:
        methods = methods_str.split(",")
        return [cls(method.strip().upper()) for method in methods]

    @classmethod
    def enum_list_to_str_list(
        cls, methods_enum_list: list["FunctionMethodEnum"]
    ) -> list[str]:
        return [method.value for method in methods_enum_list]
