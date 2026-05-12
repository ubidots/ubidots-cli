from __future__ import annotations

import socket
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
from urllib.parse import parse_qs
from urllib.parse import urlparse

from cli.commons.exceptions import AuthorizationDeniedError
from cli.commons.exceptions import CSRFMismatchError
from cli.commons.exceptions import LoginTimeoutError
from cli.settings import settings


@dataclass
class LoopbackResult:
    code: str
    state: str


_SUCCESS_HTML = (
    b'<!doctype html><html><head><meta charset="utf-8">'
    b"<title>Login complete</title></head>"
    b"<body><h1>Login complete</h1>"
    b"<p>You can close this tab and return to your terminal.</p>"
    b"</body></html>"
)

_DENIED_HTML = (
    b'<!doctype html><html><head><meta charset="utf-8">'
    b"<title>Login cancelled</title></head>"
    b"<body><h1>Authorization denied</h1>"
    b"<p>You can close this tab.</p>"
    b"</body></html>"
)


class _CallbackHandler(BaseHTTPRequestHandler):
    server: LoopbackServer

    def log_message(self, format: str, *args) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != settings.OAUTH.CALLBACK_PATH:
            self.send_response(404)
            self.end_headers()
            return

        params = {k: v[0] for k, v in parse_qs(parsed.query).items() if v}
        if "error" in params:
            self.server.set_error(AuthorizationDeniedError())
            self._respond(self._denied_status(params["error"]), _DENIED_HTML)
            return

        code = params.get("code")
        state = params.get("state", "")
        if not code:
            self.send_response(400)
            self.end_headers()
            return

        self.server.set_result(LoopbackResult(code=code, state=state))
        self._respond(200, _SUCCESS_HTML)

    def _respond(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _denied_status(error_code: str) -> int:
        return 200 if error_code == "access_denied" else 400


class LoopbackServer(HTTPServer):
    def __init__(self, host: str | None = None, port: int | None = None) -> None:
        host = host or settings.OAUTH.LOOPBACK_HOST
        port = settings.OAUTH.LOOPBACK_PORT if port is None else port
        super().__init__((host, port), _CallbackHandler)
        self._result: LoopbackResult | None = None
        self._error: Exception | None = None
        self._done = threading.Event()
        self._lock = threading.Lock()

    def set_result(self, result: LoopbackResult) -> None:
        with self._lock:
            if self._done.is_set():
                return
            self._result = result
            self._done.set()

    def set_error(self, error: Exception) -> None:
        with self._lock:
            if self._done.is_set():
                return
            self._error = error
            self._done.set()

    def wait_for_callback(self, timeout: int | None = None) -> LoopbackResult:
        timeout = settings.OAUTH.LOGIN_TIMEOUT_SECONDS if timeout is None else timeout
        thread = threading.Thread(target=self.serve_forever, daemon=True)
        thread.start()
        try:
            if not self._done.wait(timeout=timeout):
                raise LoginTimeoutError
            if self._error is not None:
                raise self._error
            assert self._result is not None
            return self._result
        finally:
            self.shutdown()
            thread.join(timeout=2)


def assert_state_matches(received: str, expected: str) -> None:
    if not received or received != expected:
        raise CSRFMismatchError


def port_available(host: str | None = None, port: int | None = None) -> bool:
    host = host or settings.OAUTH.LOOPBACK_HOST
    port = settings.OAUTH.LOOPBACK_PORT if port is None else port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1.0)
    try:
        sock.bind((host, port))
    except OSError:
        return False
    finally:
        sock.close()
    return True
