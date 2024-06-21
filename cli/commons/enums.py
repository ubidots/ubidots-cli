from enum import Enum
from enum import StrEnum

from InquirerPy import inquirer


class MessageColorEnum(StrEnum):
    WARNING = "bright_yellow"
    SUCCESS = "bright_green"
    ERROR = "bright_red"
    INFO = "bright_blue"
    HINT = "bright_magenta"


class TableColorEnum(StrEnum):
    BRIGHT_RED = "bright_red"
    GREEN = "green"
    BRIGHT_BLUE = "bright_blue"
    MAGENTA = "magenta"
    CYAN = "cyan"
    YELLOW = "yellow"
    BRIGHT_YELLOW = "bright_yellow"
    BRIGHT_MAGENTA = "bright_magenta"


class BoolValuesEnum(Enum):
    TRUE = ("yes", "y", "true", "t", "1")
    FALSE = ("no", "n", "false", "f", "0")


class ChoosableEnum(StrEnum):
    @classmethod
    def choose(cls, message=None):
        choices = list(cls)
        if message is None:
            message = f"Choose a {cls.__name__.lower()}:"
        selected = inquirer.select(
            message=message, choices=choices, default=choices[0]
        ).execute()
        return cls(selected)
