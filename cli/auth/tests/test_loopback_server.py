import contextlib
import socket
import threading
import urllib.error
import urllib.request
from unittest import TestCase

import pytest

from cli.auth.loopback_server import LoopbackResult
from cli.auth.loopback_server import LoopbackServer
from cli.auth.loopback_server import assert_state_matches
from cli.commons.exceptions import AuthorizationDeniedError
from cli.commons.exceptions import CSRFMismatchError
from cli.commons.exceptions import LoginTimeoutError
from cli.settings import settings


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class TestAssertStateMatches(TestCase):
    def test_matching_states_return_none_silently(self):
        # Setup
        received = "abc"
        expected = "abc"
        # Action
        result = assert_state_matches(received, expected)
        # Expected
        self.assertIsNone(result)

    def test_different_states_raise_csrf_mismatch(self):
        # Setup
        received = "evil"
        expected = "good"
        # Action / Expected
        with pytest.raises(CSRFMismatchError):
            assert_state_matches(received, expected)

    def test_empty_received_state_raises_csrf_mismatch(self):
        # Setup
        received = ""
        expected = "good"
        # Action / Expected
        with pytest.raises(CSRFMismatchError):
            assert_state_matches(received, expected)


class TestLoopbackServer:
    def test_successful_callback_returns_full_loopback_result(self):
        # Setup
        port = _free_port()
        server = LoopbackServer(host="127.0.0.1", port=port)
        callback_url = (
            f"http://127.0.0.1:{port}{settings.OAUTH.CALLBACK_PATH}"
            "?code=THECODE&state=STATE"
        )
        expected_result = LoopbackResult(code="THECODE", state="STATE")
        client_timer = threading.Timer(
            0.2, lambda: urllib.request.urlopen(callback_url).read()
        )
        client_timer.start()
        # Action
        try:
            actual_result = server.wait_for_callback(timeout=3)
        finally:
            client_timer.join()
        # Expected
        assert actual_result == expected_result

    def test_access_denied_callback_raises_authorization_denied(self):
        # Setup
        port = _free_port()
        server = LoopbackServer(host="127.0.0.1", port=port)
        denied_url = (
            f"http://127.0.0.1:{port}{settings.OAUTH.CALLBACK_PATH}"
            "?error=access_denied&error_description=User+cancelled"
        )
        client_timer = threading.Timer(
            0.2, lambda: urllib.request.urlopen(denied_url).read()
        )
        client_timer.start()
        # Action / Expected
        try:
            with pytest.raises(AuthorizationDeniedError):
                server.wait_for_callback(timeout=3)
        finally:
            client_timer.join()

    def test_no_callback_within_timeout_raises_login_timeout(self):
        # Setup
        port = _free_port()
        server = LoopbackServer(host="127.0.0.1", port=port)
        # Action / Expected
        with pytest.raises(LoginTimeoutError):
            server.wait_for_callback(timeout=1)

    def test_wrong_path_callback_is_ignored_until_timeout(self):
        # Setup
        port = _free_port()
        server = LoopbackServer(host="127.0.0.1", port=port)

        def _hit_junk_path():
            with contextlib.suppress(urllib.error.HTTPError):
                urllib.request.urlopen(f"http://127.0.0.1:{port}/junk").read()

        client_timer = threading.Timer(0.2, _hit_junk_path)
        client_timer.start()
        # Action / Expected
        try:
            with pytest.raises(LoginTimeoutError):
                server.wait_for_callback(timeout=1)
        finally:
            client_timer.join()
