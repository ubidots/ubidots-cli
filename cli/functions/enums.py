from enum import Enum

from InquirerPy import inquirer

from cli.settings import settings


class ChoosableEnum(Enum):
    @classmethod
    def choose(cls, message=None):
        choices = [lang.value for lang in cls]
        if message is None:
            message = f"Choose a {cls.__name__.lower()}:"
        selected = inquirer.select(
            message=message, choices=choices, default=choices[0]
        ).execute()
        return cls(selected)


class FileExtensionEnum(Enum):
    PYTHON_EXTENSION = "py"
    NODEJS_EXTENSION = "js"


class FunctionLanguageEnum(ChoosableEnum):
    PYTHON = "python"
    NODEJS = "nodejs"

    @property
    def extension(self):
        extension_map = {
            self.PYTHON: FileExtensionEnum.PYTHON_EXTENSION,
            self.NODEJS: FileExtensionEnum.NODEJS_EXTENSION,
        }
        return extension_map[self].value

    @property
    def main_file(self):
        main_file_name = settings.FUNCTIONS.DEFAULT_MAIN_FILE_NAME
        return f"{main_file_name}.{self.extension}"
