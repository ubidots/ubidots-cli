from dataclasses import field

from podman import PodmanClient

from cli.functions.engines.abstracts.network import AbstractNetworkManager


class FunctionPodmanNetworkManager(AbstractNetworkManager):
    client: PodmanClient = field(default_factory=PodmanClient)
