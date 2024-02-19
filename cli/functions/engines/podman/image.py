from dataclasses import field

from podman import PodmanClient

from cli.functions.engines.abstracts.clients import AbstractImageDownloader


class FunctionPodmanImageDownloader(AbstractImageDownloader):
    client: PodmanClient = field(default_factory=PodmanClient)
