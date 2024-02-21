from enum import Enum


class FunctionEngineTypeEnum(Enum):
    DOCKER = "docker"
    # PODMAN = "podman"


class ContainerStatusEnum(Enum):
    RESTARTING = "restarting"
    RUNNING = "running"
    PAUSED = "paused"
    EXITED = "exited"
