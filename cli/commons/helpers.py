import socket
from contextlib import suppress
from pathlib import Path
from typing import Any

import httpx
from docker.errors import APIError
from docker.errors import NotFound

from cli.commons.settings import ARGO_API_BASE_PATH
from cli.commons.settings import ARGO_CONTAINER_NAME
from cli.commons.settings import ARGO_EXTERNAL_ADAPTER_PORT
from cli.commons.settings import ARGO_EXTERNAL_TARGET_PORT
from cli.commons.settings import ARGO_HOSTNAME
from cli.commons.settings import ARGO_IMAGE_NAME
from cli.commons.settings import ARGO_INTERNAL_ADAPTER_PORT
from cli.commons.settings import ARGO_INTERNAL_TARGET_PORT
from cli.commons.settings import ARGO_LABEL_KEY
from cli.commons.settings import HOST_BIND

_PAUSED = "paused"
_EXITED = "exited"
_RUNNING = "running"


# ── Port utilities ─────────────────────────────────────────────────────────────


def is_port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        try:
            sock.bind(("localhost", port))
            return True
        except OSError:
            return False


def find_available_ports(
    ports: list[int],
    start_range: int = 8040,
    end_range: int = 65535,
) -> list[int]:
    available: list[int] = [port for port in ports if is_port_available(port)]
    if len(available) < len(ports):
        for port in range(start_range, end_range + 1):
            if len(available) == len(ports):
                break
            if port not in available and is_port_available(port):
                available.append(port)
    if len(available) < len(ports):
        raise RuntimeError(
            f"Could not find {len(ports)} available ports (found {len(available)})"
        )
    return available


# ── Argo container manager ─────────────────────────────────────────────────────


def _get_external_port(container: Any, internal_port: str) -> int:
    mapping = (container.ports or {}).get(internal_port, [])
    if mapping:
        return int(mapping[0]["HostPort"])
    raise ValueError(f"No external port for {internal_port}")


def argo_container_manager(
    container_manager: Any,
    client: Any,
    network: Any,
    image_name: str = ARGO_IMAGE_NAME,
    frie_label: str | None = None,
):
    """Start or reuse the shared Argo container.

    Unconditionally mounts ~/.ubidots_cli/pages/ at /pages/ (read-only).
    Creates the directory if it does not exist.
    Returns (container, argo_adapter_port, argo_target_port).
    """
    pages_workspace = Path.home() / ".ubidots_cli" / "pages"
    pages_workspace.mkdir(parents=True, exist_ok=True)

    def _check() -> Any | None:
        container = None
        with suppress(NotFound):
            container = client.client.containers.get(ARGO_CONTAINER_NAME)
        if container is None:
            return None
        if container.status in (_PAUSED, _EXITED):
            try:
                container.restart()
                container.reload()
            except APIError:
                container.remove()
                return None
            return container
        if container.status == _RUNNING and frie_label:
            port = _get_external_port(container, ARGO_INTERNAL_ADAPTER_PORT)
            url = f"http://{HOST_BIND}:{port}/{ARGO_API_BASE_PATH}/~{frie_label}"
            resp = httpx.get(url, timeout=5.0)
            if resp.status_code == httpx.codes.OK:
                httpx.delete(url, timeout=5.0)
        return container

    container = _check()
    if container is None:
        adapter_port, target_port = find_available_ports(
            [ARGO_EXTERNAL_ADAPTER_PORT, ARGO_EXTERNAL_TARGET_PORT]
        )
        container = container_manager.start(
            image_name=image_name,
            container_name=ARGO_CONTAINER_NAME,
            network_name=network.name,
            labels={ARGO_LABEL_KEY: ARGO_CONTAINER_NAME},
            ports={
                ARGO_INTERNAL_ADAPTER_PORT: (HOST_BIND, adapter_port),
                ARGO_INTERNAL_TARGET_PORT: (HOST_BIND, target_port),
            },
            volumes={
                str(pages_workspace): {"bind": "/pages", "mode": "ro"},
            },
            hostname=ARGO_HOSTNAME,
        )
    else:
        adapter_port = _get_external_port(container, ARGO_INTERNAL_ADAPTER_PORT)
        target_port = _get_external_port(container, ARGO_INTERNAL_TARGET_PORT)
    return container, adapter_port, target_port


# ── verify_and_fetch_images ────────────────────────────────────────────────────


def verify_and_fetch_images(client: Any, image_names: list[str]) -> None:
    """Pull Docker/Podman images, raising on failure.

    Works on any client implementing get_validator() and get_downloader().
    Exceptions from validate_engine_installed() and pull_image() propagate as-is.
    """
    validator = client.get_validator()
    for image_name in image_names:
        validator.validate_engine_installed()
        downloader = client.get_downloader()
        downloader.pull_image(image_name=image_name)
