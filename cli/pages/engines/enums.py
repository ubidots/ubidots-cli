from cli.compat import StrEnum


class PageEngineTypeEnum(StrEnum):
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
