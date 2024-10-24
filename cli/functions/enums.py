from enum import Enum
from enum import auto

from cli.compat import StrEnum
from cli.settings import settings


class FunctionMainFileExtensionEnum(StrEnum):
    PYTHON_EXTENSION = "py"
    NODEJS_EXTENSION = "js"


class FunctionHandlerFileExtensionEnum(StrEnum):
    PYTHON_EXTENSION = "py"
    NODEJS_EXTENSION = "mjs"


class FunctionLayerTypeEnum(StrEnum):
    LITE = "lite"
    BASE = "base"
    FULL = "full"


class FunctionPythonVersionEnum(StrEnum):
    PYTHON_3_9 = "python3.9"
    PYTHON_3_11 = "python3.11"


class FunctionNodejsVersionEnum(StrEnum):
    NODEJS_20 = "nodejs20.x"


class FunctionPythonRuntimeLayerTypeEnum(StrEnum):
    PYTHON_3_9_LITE = (
        f"{FunctionPythonVersionEnum.PYTHON_3_9}:{FunctionLayerTypeEnum.LITE}"
    )
    PYTHON_3_9_BASE = (
        f"{FunctionPythonVersionEnum.PYTHON_3_9}:{FunctionLayerTypeEnum.BASE}"
    )
    PYTHON_3_9_FULL = (
        f"{FunctionPythonVersionEnum.PYTHON_3_9}:{FunctionLayerTypeEnum.FULL}"
    )
    PYTHON_3_11_LITE = (
        f"{FunctionPythonVersionEnum.PYTHON_3_11}:{FunctionLayerTypeEnum.LITE}"
    )
    PYTHON_3_11_BASE = (
        f"{FunctionPythonVersionEnum.PYTHON_3_11}:{FunctionLayerTypeEnum.BASE}"
    )
    PYTHON_3_11_FULL = (
        f"{FunctionPythonVersionEnum.PYTHON_3_11}:{FunctionLayerTypeEnum.FULL}"
    )


class FunctionNodejsRuntimeLayerTypeEnum(StrEnum):
    NODEJS_20_LITE = (
        f"{FunctionNodejsVersionEnum.NODEJS_20}:{FunctionLayerTypeEnum.LITE}"
    )
    NODEJS_20_BASE = (
        f"{FunctionNodejsVersionEnum.NODEJS_20}:{FunctionLayerTypeEnum.BASE}"
    )


# TODO: Ensure to update both FunctionPythonRuntimeLayerTypeEnum and FunctionNodejsRuntimeLayerTypeEnum here
# NOTE: Changes made in FunctionPythonRuntimeLayerTypeEnum or FunctionNodejsRuntimeLayerTypeEnum should be reflected here
class FunctionRuntimeLayerTypeEnum(StrEnum):
    # FunctionPythonRuntimeLayerTypeEnum
    PYTHON_3_9_LITE = (
        f"{FunctionPythonVersionEnum.PYTHON_3_9}:{FunctionLayerTypeEnum.LITE}"
    )
    PYTHON_3_9_BASE = (
        f"{FunctionPythonVersionEnum.PYTHON_3_9}:{FunctionLayerTypeEnum.BASE}"
    )
    PYTHON_3_9_FULL = (
        f"{FunctionPythonVersionEnum.PYTHON_3_9}:{FunctionLayerTypeEnum.FULL}"
    )
    PYTHON_3_11_LITE = (
        f"{FunctionPythonVersionEnum.PYTHON_3_11}:{FunctionLayerTypeEnum.LITE}"
    )
    PYTHON_3_11_BASE = (
        f"{FunctionPythonVersionEnum.PYTHON_3_11}:{FunctionLayerTypeEnum.BASE}"
    )
    PYTHON_3_11_FULL = (
        f"{FunctionPythonVersionEnum.PYTHON_3_11}:{FunctionLayerTypeEnum.FULL}"
    )
    # FunctionNodejsRuntimeLayerTypeEnum
    NODEJS_20_LITE = (
        f"{FunctionNodejsVersionEnum.NODEJS_20}:{FunctionLayerTypeEnum.LITE}"
    )
    NODEJS_20_BASE = (
        f"{FunctionNodejsVersionEnum.NODEJS_20}:{FunctionLayerTypeEnum.BASE}"
    )


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

    @property
    def main_file(self):
        main_file_name = settings.FUNCTIONS.DEFAULT_MAIN_FILE_NAME
        return f"{main_file_name}.{self.extension}"

    @property
    def version(self):
        version_map = {
            self.PYTHON: FunctionPythonVersionEnum,
            self.NODEJS: FunctionNodejsVersionEnum,
        }
        return version_map[self]

    @property
    def runtime(self):
        runtime_map = {
            self.PYTHON: FunctionPythonRuntimeLayerTypeEnum,
            self.NODEJS: FunctionNodejsRuntimeLayerTypeEnum,
        }
        return runtime_map[self]

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
