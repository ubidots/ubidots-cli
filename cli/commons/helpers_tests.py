import socket

from cli.commons.helpers import find_available_ports
from cli.commons.helpers import is_port_available


def _get_free_ports(count: int) -> list[int]:
    """Allocate temporary free ports, then close and return them."""
    sockets = []
    try:
        for _ in range(count):
            s = socket.socket()
            s.bind(("localhost", 0))
            sockets.append(s)
        return [s.getsockname()[1] for s in sockets]
    finally:
        for s in sockets:
            s.close()


def test_is_port_available_when_free():
    # Find a port that is actually free
    with socket.socket() as s:
        s.bind(("localhost", 0))
        free_port = s.getsockname()[1]
    # Port is free after socket closes
    assert is_port_available(free_port) is True


def test_is_port_available_when_occupied():
    with socket.socket() as s:
        s.bind(("localhost", 0))
        occupied_port = s.getsockname()[1]
        # Port is occupied while socket is open
        assert is_port_available(occupied_port) is False


def test_find_available_ports_returns_requested_count():
    candidate_ports = _get_free_ports(2)
    ports = find_available_ports(candidate_ports)
    assert len(ports) == 2
    for p in ports:
        assert is_port_available(p)


def test_find_available_ports_falls_back_when_occupied():
    with socket.socket() as s:
        s.bind(("localhost", 0))
        occupied = s.getsockname()[1]
        # Use a safe range that doesn't exceed port limit
        start_range = occupied + 1 if occupied < 65535 else 1024
        end_range = min(start_range + 50, 65535)
        result = find_available_ports(
            [occupied], start_range=start_range, end_range=end_range
        )
    assert len(result) == 1
    assert result[0] != occupied
