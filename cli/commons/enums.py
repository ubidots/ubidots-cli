from enum import Enum


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
