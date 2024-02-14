from podman import PodmanClient

from cli.functions.engines.helpers import AbstractImageDownloader


class PodmanImageDownloader(AbstractImageDownloader):
    def __init__(self, client: PodmanClient):
        super().__init__(client)
