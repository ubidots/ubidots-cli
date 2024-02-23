from dataclasses import field

from podman import PodmanClient

from cli.functions.engines.abstracts.client import AbstractImageDownloader


class FunctionPodmanImageDownloader(AbstractImageDownloader):
    client: PodmanClient = field(default_factory=PodmanClient)
