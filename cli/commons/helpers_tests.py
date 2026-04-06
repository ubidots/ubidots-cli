import socket

from cli.commons.helpers import find_available_ports
from cli.commons.helpers import is_port_available


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
    ports = find_available_ports([55555, 55556])
    assert len(ports) == 2
    for p in ports:
        assert is_port_available(p)


def test_find_available_ports_falls_back_when_occupied():
    with socket.socket() as s:
        s.bind(("localhost", 0))
        occupied = s.getsockname()[1]
        result = find_available_ports(
            [occupied], start_range=occupied + 1, end_range=occupied + 50
        )
    assert len(result) == 1
    assert result[0] != occupied
