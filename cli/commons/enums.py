from enum import Enum
from enum import EnumMeta
from enum import StrEnum

from InquirerPy import inquirer


class MessageColorEnum(StrEnum):
    WARNING = "bright_yellow"
    SUCCESS = "bright_green"
    ERROR = "bright_red"
    INFO = "bright_blue"


class TableColorEnum(Enum):
    BRIGHT_RED = "bright_red"
    GREEN = "green"
    BRIGHT_BLUE = "bright_blue"
    MAGENTA = "magenta"
    CYAN = "cyan"
    YELLOW = "yellow"
    BRIGHT_YELLOW = "bright_yellow"
    BRIGHT_MAGENTA = "bright_magenta"


class HTTPMethodEnum(Enum):
    GET = "GET"
    POST = "POST"
    PATCH = "PATCH"
    PUT = "PUT"
    DELETE = "DELETE"


class RequestErrorEnum(Enum):
    HTTP_ERROR = "HTTPError"
    CONNECTION_ERROR = "ConnectionError"
    TIMEOUT = "Timeout"
    REQUEST_EXCEPTION = "RequestException"
    UNKNOWN_ERROR = "UnknownError"


class CombinerEnum:
    @staticmethod
    def combine(enum_base: EnumMeta = Enum, *enums) -> EnumMeta:
        if not all(isinstance(e, enum_base) for enum in enums for e in enum):
            error_message = (
                "All enums to be combined must be of the same base type as 'enum_base'."
            )
            raise ValueError(error_message)

        combined = {}
        name_parts = [enum.__name__ for enum in enums]
        combined_name = "_".join(name_parts) + "_Combined"

        for enum in enums:
            combined.update({e.name: e.value for e in enum})

        return enum_base(combined_name, combined)


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
