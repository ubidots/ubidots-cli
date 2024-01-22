from enum import Enum


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
