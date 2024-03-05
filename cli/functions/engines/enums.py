from enum import StrEnum


class FunctionEngineTypeEnum(StrEnum):
    DOCKER = "DOCKER"
    # PODMAN = "podman"


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
