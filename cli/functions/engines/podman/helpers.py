from dataclasses import dataclass

from podman import PodmanClient

from cli.functions.engines.helpers import AbstractImageDownloader


@dataclass
class PodmanImageDownloader(AbstractImageDownloader):
    client: PodmanClient
