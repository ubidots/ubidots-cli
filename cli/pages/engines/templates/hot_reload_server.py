#!/usr/bin/env python3
"""Hot reload subprocess for pages dev server.

Usage:
    python hot_reload_server.py \
        --page-workspace /path/to/workspace \
        --page-name my-page-abc12345 \
        --port 9001
"""
import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

_INTERNAL_FILES = {
    "index.html",
    ".hot_reload.log",
    ".copy_watcher.log",
    ".source_path",
}
_MAX_ERRORS = 10

_sse_clients: list = []
_errors: list = []
_start_time = time.time()
_lock = threading.Lock()


def _push_reload() -> None:
    with _lock:
        dead = []
        for client in _sse_clients:
            try:
                client.write(b"data: reload\n\n")
                client.flush()
            except Exception:
                dead.append(client)
        for c in dead:
            _sse_clients.remove(c)


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, format_, *args):
        pass  # Suppress default request logging

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path == "/__dev/reload":
            self._sse()
        elif self.path == "/__dev/status":
            self._status()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/__dev/error":
            self._capture_error()
        else:
            self.send_response(404)
            self.end_headers()

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self._cors()
        self.end_headers()
        with _lock:
            _sse_clients.append(self.wfile)
        try:
            while True:
                self.wfile.write(b": ping\n\n")
                self.wfile.flush()
                time.sleep(15)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with _lock:
                if self.wfile in _sse_clients:
                    _sse_clients.remove(self.wfile)

    def _status(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.end_headers()
        payload = {
            "uptime_seconds": int(time.time() - _start_time),
            "errors": list(_errors),
        }
        self.wfile.write(json.dumps(payload).encode())

    def _capture_error(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            error = json.loads(body)
            with _lock:
                _errors.append(error)
                if len(_errors) > _MAX_ERRORS:
                    _errors.pop(0)
            print(
                f"[browser error] {error.get('message', '')} "
                f"({error.get('source', '')}:{error.get('line', '')})",
                flush=True,
            )
        except json.JSONDecodeError:
            pass
        except Exception as exc:
            print(f"[browser error capture failed] {exc}", flush=True)
        self.send_response(200)
        self._cors()
        self.end_headers()


class _ChangeHandler(FileSystemEventHandler):
    def __init__(self):
        self._timer: threading.Timer | None = None

    def on_modified(self, event):
        if event.is_directory:
            return
        if Path(event.src_path).name in _INTERNAL_FILES:
            return
        self._schedule()

    on_created = on_modified

    def _schedule(self):
        if self._timer:
            self._timer.cancel()
        self._timer = threading.Timer(0.5, self._reload)
        self._timer.start()

    def _reload(self):
        _push_reload()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--page-workspace", required=True)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()

    workspace = Path(args.page_workspace)
    handler = _ChangeHandler()

    observer = Observer()
    observer.schedule(handler, str(workspace), recursive=True)
    observer.start()

    server = ThreadingHTTPServer(("localhost", args.port), _Handler)
    print(f"[hot-reload] port={args.port} workspace={workspace}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    main()
