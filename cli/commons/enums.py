from enum import Enum
from enum import StrEnum


class MessageColorEnum(StrEnum):
    WARNING = "bright_yellow"
    SUCCESS = "bright_green"
    ERROR = "bright_red"
    INFO = "bright_blue"


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
