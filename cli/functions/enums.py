from enum import Enum
from enum import StrEnum
from enum import auto

from cli.commons.enums import ChoosableEnum
from cli.settings import settings


class FunctionMainFileExtensionEnum(StrEnum):
    PYTHON_EXTENSION = "py"
    NODEJS_EXTENSION = "js"


class FunctionLayerTypeEnum(StrEnum):
    LITE = "lite"
    BASE = "base"
    FULL = "full"


class FunctionPythonVersionEnum(ChoosableEnum):
    PYTHON_3_9 = "python3.9"
    PYTHON_3_11 = "python3.11"


class FunctionNodejsVersionEnum(ChoosableEnum):
    NODEJS_16 = "nodejs16.x"
    NODEJS_20 = "nodejs20.x"


class FunctionPythonRuntimeLayerTypeEnum(ChoosableEnum):
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


class FunctionNodejsRuntimeLayerTypeEnum(ChoosableEnum):
    NODEJS_16_LITE = (
        f"{FunctionNodejsVersionEnum.NODEJS_16}:{FunctionLayerTypeEnum.LITE}"
    )
    NODEJS_16_BASE = (
        f"{FunctionNodejsVersionEnum.NODEJS_16}:{FunctionLayerTypeEnum.BASE}"
    )
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
    NODEJS_16_LITE = (
        f"{FunctionNodejsVersionEnum.NODEJS_16}:{FunctionLayerTypeEnum.LITE}"
    )
    NODEJS_16_BASE = (
        f"{FunctionNodejsVersionEnum.NODEJS_16}:{FunctionLayerTypeEnum.BASE}"
    )
    NODEJS_20_LITE = (
        f"{FunctionNodejsVersionEnum.NODEJS_20}:{FunctionLayerTypeEnum.LITE}"
    )
    NODEJS_20_BASE = (
        f"{FunctionNodejsVersionEnum.NODEJS_20}:{FunctionLayerTypeEnum.BASE}"
    )


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

    def choose_runtime(self, message: str = "Select a runtime:"):
        return self.runtime.choose(message)


class FunctionProjectValidationTypeEnum(Enum):
    MANIFEST_FILE = auto()
    MAIN_FILE_PRESENCE = auto()


class FunctionMethodEnum(StrEnum):
    GET = "GET"
    POST = "POST"
