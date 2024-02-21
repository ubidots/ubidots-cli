from enum import Enum
from enum import StrEnum
from enum import auto

from InquirerPy import inquirer

from cli.settings import settings


class ChoosableEnum(Enum):
    @classmethod
    def choose(cls, message=None):
        choices = [member.value for member in cls]
        if message is None:
            message = f"Choose a {cls.__name__.lower()}:"
        selected = inquirer.select(
            message=message, choices=choices, default=choices[0]
        ).execute()
        return cls(selected)


class FunctionMainFileExtensionEnum(Enum):
    PYTHON_EXTENSION = "py"
    NODEJS_EXTENSION = "js"


class FunctionLayerTypeEnum(Enum):
    LITE = "lite"
    BASE = "base"
    FULL = "full"


class FunctionPythonVersionEnum(ChoosableEnum):
    # PYTHON_3_6 = deprecated("python:3.6")
    # PYTHON_3_7 = deprecated("python:3.7")
    PYTHON_3_9 = "python3.9"
    PYTHON_3_11 = "python3.11"


class FunctionNodejsVersionEnum(ChoosableEnum):
    # NODEJS_10 = deprecated("nodejs:10")
    NODEJS_16 = "nodejs16.x"


class FunctionPythonRuntimeLayerTypeEnum(ChoosableEnum):
    # PYTHON_3_6 = FunctionPythonVersionEnum.PYTHON_3_6.value
    # PYTHON_3_7 = FunctionPythonVersionEnum.PYTHON_3_7.value
    PYTHON_3_9_LITE = f"{FunctionPythonVersionEnum.PYTHON_3_9.value}:{FunctionLayerTypeEnum.LITE.value}"
    PYTHON_3_9_BASE = f"{FunctionPythonVersionEnum.PYTHON_3_9.value}:{FunctionLayerTypeEnum.BASE.value}"
    PYTHON_3_9_FULL = f"{FunctionPythonVersionEnum.PYTHON_3_9.value}:{FunctionLayerTypeEnum.FULL.value}"
    PYTHON_3_11_LITE = f"{FunctionPythonVersionEnum.PYTHON_3_11.value}:{FunctionLayerTypeEnum.LITE.value}"
    PYTHON_3_11_BASE = f"{FunctionPythonVersionEnum.PYTHON_3_11.value}:{FunctionLayerTypeEnum.BASE.value}"
    PYTHON_3_11_FULL = f"{FunctionPythonVersionEnum.PYTHON_3_11.value}:{FunctionLayerTypeEnum.FULL.value}"


class FunctionNodejsRuntimeLayerTypeEnum(ChoosableEnum):
    # NODEJS_10 = FunctionNodejsVersionEnum.NODEJS_10.value
    NODEJS_16_LITE = f"{FunctionNodejsVersionEnum.NODEJS_16.value}:{FunctionLayerTypeEnum.LITE.value}"
    NODEJS_16_BASE = f"{FunctionNodejsVersionEnum.NODEJS_16.value}:{FunctionLayerTypeEnum.BASE.value}"


class FunctionLanguageEnum(ChoosableEnum):
    PYTHON = "python"
    NODEJS = "nodejs"

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
        return f"{main_file_name}.{self.extension.value}"

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

    def choose_runtime(self, message: str = "Select a runtime:"):
        return self.runtime.choose(message)


class FunctionProjectValidationTypeEnum(Enum):
    MANIFEST_FILE = auto()
    MAIN_FILE_PRESENCE = auto()
    FILE_NAMES = auto()
    FILE_COUNT = auto()
    INDIVIDUAL_FILE_SIZE = auto()


class FunctionMethodEnum(StrEnum):
    GET = "GET"
    POST = "POST"
