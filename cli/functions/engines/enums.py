from cli.compat import StrEnum


class FunctionEngineTypeEnum(StrEnum):
    DOCKER = "DOCKER"
    PODMAN = "PODMAN"


class ContainerStatusEnum(StrEnum):
    RESTARTING = "restarting"
    RUNNING = "running"
    PAUSED = "paused"
    EXITED = "exited"


class ContainerNetworkModeEnum(StrEnum):
    BRIDGE = "bridge"
    NONE = "none"
    HOST = "host"


class TargetTypeEnum(StrEnum):
    RIE_FUNCTION = "rie_function"
    RIE_FUNCTION_RAW = "rie_function_raw"


class MiddlewareTypeEnum(StrEnum):
    ALLOWED_METHODS = "allowed_methods"
    CORS = "cors"


class ArgoMethodEnum(StrEnum):
    GET = "GET"
    POST = "POST"
    OPTIONS = "OPTIONS"
