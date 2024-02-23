from enum import StrEnum


class FunctionEngineTypeEnum(StrEnum):
    DOCKER = "DOCKER"
    # PODMAN = "podman"


class ContainerStatusEnum(StrEnum):
    RESTARTING = "restarting"
    RUNNING = "running"
    PAUSED = "paused"
    EXITED = "exited"
