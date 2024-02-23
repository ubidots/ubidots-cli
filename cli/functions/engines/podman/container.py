from dataclasses import field

from podman import PodmanClient

from cli.functions.engines.abstracts.client import AbstractContainerManager


class FunctionPodmanContainerManager(AbstractContainerManager):
    client: PodmanClient = field(default_factory=PodmanClient)
