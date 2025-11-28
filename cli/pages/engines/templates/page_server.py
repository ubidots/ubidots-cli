import os
import json
import time
import threading
from pathlib import Path

import tomli
from flask import Flask
from flask import render_template_string
from flask import send_from_directory
from flask import Response
from flask_cors import CORS

# The page files are mounted at /app/page
BASE_DIR = "/app/page"
TEMPLATE_FILE = "/app/template.html"

# Configure Flask without hardcoded static folder (we handle static serving manually)
app = Flask(__name__, static_folder=None)

# Enable CORS for all routes
CORS(
    app,
    origins="*",
    allow_headers="*",
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
)

# CDN URLs from environment variables (passed from CLI settings)
CDN_URLS = {
    "HTML_CANVAS_LIBRARY_URL": os.environ.get("HTML_CANVAS_LIBRARY_URL", ""),
    "REACT_URL": os.environ.get("REACT_URL", ""),
    "REACT_DOM_URL": os.environ.get("REACT_DOM_URL", ""),
    "BABEL_STANDALONE_URL": os.environ.get("BABEL_STANDALONE_URL", ""),
    "VULCANUI_JS_URL": os.environ.get("VULCANUI_JS_URL", ""),
    "VULCANUI_CSS_URL": os.environ.get("VULCANUI_CSS_URL", ""),
}

# Hot reload configuration from environment variables
HOT_RELOAD_ENABLED = os.environ.get("HOT_RELOAD_ENABLED", "false").lower() == "true"
HOT_RELOAD_ENDPOINT = os.environ.get("HOT_RELOAD_ENDPOINT", "/__dev/reload")
HOT_RELOAD_WATCH_EXTENSIONS = os.environ.get("HOT_RELOAD_WATCH_EXTENSIONS", "").split(
    ","
)
HOT_RELOAD_IGNORE_PATTERNS = os.environ.get("HOT_RELOAD_IGNORE_PATTERNS", "").split(",")
HOT_RELOAD_DEBOUNCE_MS = int(os.environ.get("HOT_RELOAD_DEBOUNCE_MS", "500"))

# Global variable to store SSE clients
sse_clients = set()


def load_page_config():
    """Load and parse manifest.toml and body.html"""
    manifest_path = Path(BASE_DIR) / "manifest.toml"
    body_path = Path(BASE_DIR) / "body.html"

    # Read manifest.toml
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest.toml in {BASE_DIR}")

    with open(manifest_path, "rb") as f:
        toml_data = tomli.load(f)

    page_config = toml_data.get("page", {})

    # Read body.html
    if not body_path.exists():
        raise FileNotFoundError(f"Missing body.html in {BASE_DIR}")

    with open(body_path, "r", encoding="utf-8") as f:
        body_html = f.read()

    page_config["body"] = body_html

    return page_config


def get_allowed_files():
    """Get allowed files from manifest.toml (static_paths + library files)"""
    try:
        page_config = load_page_config()

        # Get static directories
        static_paths = page_config.get("static_paths", [])

        # Get files referenced in libraries
        library_files = set()

        # Extract files from js_libraries
        for lib in page_config.get("js_libraries", []):
            if isinstance(lib, dict) and "src" in lib:
                src = lib["src"]
                # Only include local files (not URLs)
                if not src.startswith(("http://", "https://", "//")):
                    library_files.add(src)

        # Extract files from css_libraries
        for lib in page_config.get("css_libraries", []):
            if isinstance(lib, dict) and "href" in lib:
                href = lib["href"]
                # Only include local files (not URLs)
                if not href.startswith(("http://", "https://", "//")):
                    library_files.add(href)

        return {"static_paths": static_paths, "library_files": library_files}
    except Exception:
        # Fallback to empty configuration if manifest can't be read
        return {"static_paths": [], "library_files": set()}


def is_file_allowed(requested_path: str, allowed_config: dict) -> bool:
    """Check if the requested path is allowed (in static dirs or library files)"""
    static_paths = allowed_config.get("static_paths", [])
    library_files = allowed_config.get("library_files", set())

    # Normalize the requested path
    requested_path = requested_path.strip("/")

    # Check if it's a library file (exact match)
    if requested_path in library_files:
        return True

    # Check if it's within any static directory
    for static_path in static_paths:
        static_path = static_path.strip("/")

        # Check if the requested path starts with this static path
        if (
            requested_path.startswith(static_path + "/")
            or requested_path == static_path
        ):
            return True

    return False


def convert_libraries(libraries):
    """Convert library dictionaries to template-compatible format"""

    class LibraryWrapper:
        def __init__(self, data):
            self.items = list(data.items())

    return [LibraryWrapper(lib) for lib in libraries]


def get_hot_reload_url():
    """Get the correct hot reload SSE URL based on routing mode"""
    routing_mode = os.environ.get("ROUTING_MODE", "subdomain")
    hot_reload_port = os.environ.get("HOT_RELOAD_PORT", "9000")
    external_port = os.environ.get("EXTERNAL_PORT")

    if routing_mode == "port":
        # Port mode: Use the main external port (same as page)
        port = external_port if external_port else "8090"
        return f"http://localhost:{port}{HOT_RELOAD_ENDPOINT}"
    else:
        # Path and subdomain modes: Use dedicated hot reload port
        return f"http://localhost:{hot_reload_port}{HOT_RELOAD_ENDPOINT}"


def inject_hot_reload_script(html_content):
    """Inject hot reload script into HTML if hot reload is enabled"""
    if not HOT_RELOAD_ENABLED:
        return html_content

    # Get the correct SSE URL for the current routing mode
    sse_url = get_hot_reload_url()

    reload_script = f"""
    <script>
        (function() {{
            console.log('Hot reload: Connecting to {sse_url}');
            const eventSource = new EventSource('{sse_url}');
            eventSource.onmessage = function(event) {{
                if (event.data === 'reload') {{
                    console.log('Hot reload: Reloading page...');
                    window.location.reload();
                }} else if (event.data === 'connected') {{
                    console.log('Hot reload: Connected successfully');
                }}
            }};
            eventSource.onerror = function(event) {{
                console.log('Hot reload: Connection lost, retrying...');
            }};
        }})();
    </script>
    """

    # Try to inject before </body>, otherwise append to end
    if "</body>" in html_content:
        html_content = html_content.replace("</body>", reload_script + "</body>")
    else:
        html_content += reload_script

    return html_content


def render_page():
    """Render the page using the template"""
    # Load template
    if not Path(TEMPLATE_FILE).exists():
        return {"error": "Template file not found"}, 500

    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        template_content = f.read()

    # Load page configuration
    try:
        page_config = load_page_config()
    except Exception as e:
        return {"error": f"Failed to load page config: {str(e)}"}, 500

    # Convert libraries to template format
    page_config["js_libraries"] = convert_libraries(page_config.get("js_libraries", []))
    page_config["css_libraries"] = convert_libraries(
        page_config.get("css_libraries", [])
    )
    page_config["link_libraries"] = convert_libraries(
        page_config.get("link_libraries", [])
    )
    page_config["js_thirdparty_libraries"] = convert_libraries(
        page_config.get("js_thirdparty_libraries", [])
    )
    page_config["css_thirdparty_libraries"] = convert_libraries(
        page_config.get("css_thirdparty_libraries", [])
    )
    page_config["link_thirdparty_libraries"] = convert_libraries(
        page_config.get("link_thirdparty_libraries", [])
    )

    # Construct full page URL for window.staticUrl based on routing mode
    page_name = os.environ.get("PAGE_NAME", "unknown")
    routing_mode = os.environ.get("ROUTING_MODE", "subdomain")

    # Get port configuration from environment variables (passed from container helper)
    flask_manager_port = os.environ.get("FLASK_MANAGER_PORT", "8044")
    external_port = os.environ.get("EXTERNAL_PORT")

    if routing_mode == "path":
        base_url = f"http://localhost:{flask_manager_port}/{page_name}"
    elif routing_mode == "port":
        # For port routing, use the actual external port assigned to this container
        port = external_port if external_port else "8090"
        base_url = f"http://localhost:{port}"
    else:
        # Default to subdomain routing
        base_url = f"http://{page_name}.localhost:{flask_manager_port}"

    # Prepare template context
    context = {"page": page_config, "BASE_URL": base_url, **CDN_URLS}

    # Render template
    rendered_html = render_template_string(template_content, **context)

    # Inject hot reload script if enabled
    rendered_html = inject_hot_reload_script(rendered_html)

    return rendered_html


@app.route("/")
def serve_root():
    """Serve the rendered page at root"""
    return render_page()


@app.route("/<path:path>")
def serve_file(path):
    """Serve files from allowed static directories and library files only"""
    # Get allowed files configuration from manifest.toml
    allowed_config = get_allowed_files()

    # Check if the requested path is allowed
    if not is_file_allowed(path, allowed_config):
        return {"error": "File not found"}, 404

    try:
        return send_from_directory(BASE_DIR, path)
    except Exception:
        return {"error": "File not found"}, 404


def send_reload_signal():
    """Send reload signal to all connected SSE clients"""
    if not HOT_RELOAD_ENABLED:
        return

    # Create a copy of the set to avoid modification during iteration
    clients_to_remove = set()

    for client in sse_clients.copy():
        try:
            client.put("data: reload\n\n")
        except Exception:
            # Client disconnected, mark for removal
            clients_to_remove.add(client)

    # Remove disconnected clients
    sse_clients.difference_update(clients_to_remove)


def setup_file_watcher():
    """Setup file watcher for hot reload"""
    if not HOT_RELOAD_ENABLED:
        return

    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
        import fnmatch

        class ReloadHandler(FileSystemEventHandler):
            def __init__(self):
                self.last_reload_time = 0
                self.pending_reload = False
                self.reload_timer = None

            def should_ignore_file(self, file_path):
                """Check if file should be ignored based on patterns"""
                file_name = os.path.basename(file_path)

                # Ignore common temporary and system files
                temp_patterns = [
                    "*.tmp",
                    "*.temp",
                    "*~",
                    "*.swp",
                    "*.swo",
                    ".#*",
                    "#*#",
                    "*.bak",
                    "*.orig",
                    # Editor temporary files
                    "*.tmp.*",
                    "*_tmp_*",
                    "*.autosave",
                    # Browser/dev tools files
                    "*.crdownload",
                    "*.part",
                ]

                for pattern in temp_patterns:
                    if fnmatch.fnmatch(file_name, pattern):
                        return True

                # Check user-defined ignore patterns
                for pattern in HOT_RELOAD_IGNORE_PATTERNS:
                    if pattern and fnmatch.fnmatch(file_name, pattern):
                        return True

                # Ignore hidden files and directories (starting with .)
                if file_name.startswith(".") and file_name not in [".page.html"]:
                    return True

                # Check file extensions (if specified)
                if HOT_RELOAD_WATCH_EXTENSIONS:
                    file_ext = os.path.splitext(file_name)[1]
                    if file_ext not in HOT_RELOAD_WATCH_EXTENSIONS:
                        return True

                return False

            def trigger_reload_after_delay(self):
                """Trigger reload after debounce delay"""
                import threading

                def delayed_reload():
                    time.sleep(HOT_RELOAD_DEBOUNCE_MS / 1000.0)  # Convert to seconds
                    if self.pending_reload:
                        self.pending_reload = False
                        print("Hot reload: Triggering reload after debounce")
                        send_reload_signal()

                # Cancel previous timer if exists
                if self.reload_timer and self.reload_timer.is_alive():
                    return  # Already have a pending reload

                self.pending_reload = True
                self.reload_timer = threading.Thread(target=delayed_reload, daemon=True)
                self.reload_timer.start()

            def on_any_event(self, event):
                if event.is_directory:
                    return

                # Check if file should be ignored
                if self.should_ignore_file(event.src_path):
                    return

                # Only process actual file modifications and creations
                if event.event_type not in ["modified", "created"]:
                    return

                print(f"Hot reload: File {event.event_type}: {event.src_path}")

                # Use debounced reload to prevent multiple rapid reloads
                self.trigger_reload_after_delay()

        # Start file watcher in background thread
        observer = Observer()
        observer.schedule(ReloadHandler(), BASE_DIR, recursive=True)
        observer.start()

        print(f"Hot reload: Watching {BASE_DIR} for changes")
        print(f"Hot reload: SSE endpoint: {HOT_RELOAD_ENDPOINT}")
        print(f"Hot reload: Extensions: {HOT_RELOAD_WATCH_EXTENSIONS}")
        print(f"Hot reload: Debounce: {HOT_RELOAD_DEBOUNCE_MS}ms")

        return observer

    except ImportError:
        print("Warning: watchdog not available, hot reload disabled")
        return None
    except Exception as e:
        print(f"Warning: Failed to setup file watcher: {e}")
        return None


def start_hot_reload_server():
    """Start a separate Flask server for hot reload SSE on port 5001"""
    if not HOT_RELOAD_ENABLED:
        return

    # Create a separate Flask app for hot reload
    hot_reload_app = Flask(__name__, static_folder=None)
    CORS(hot_reload_app, origins="*", allow_headers="*", methods=["GET", "OPTIONS"])

    @hot_reload_app.route(HOT_RELOAD_ENDPOINT)
    def hot_reload_sse():
        """Server-Sent Events endpoint for hot reload"""
        import queue

        def event_stream():
            client_queue = queue.Queue()
            sse_clients.add(client_queue)

            try:
                # Send initial connection message
                yield "data: connected\n\n"

                while True:
                    try:
                        # Wait for reload signal
                        message = client_queue.get(timeout=30)  # 30 second timeout
                        yield message
                    except queue.Empty:
                        # Send heartbeat to keep connection alive
                        yield "data: heartbeat\n\n"
            except GeneratorExit:
                # Client disconnected
                sse_clients.discard(client_queue)

        return Response(
            event_stream(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            },
        )

    # Start hot reload server in background thread
    def run_hot_reload_server():
        try:
            print(f"Hot reload server starting on port 5001")
            hot_reload_app.run(host="0.0.0.0", port=5001, debug=False)
        except Exception as e:
            print(f"Hot reload server error: {e}")

    hot_reload_thread = threading.Thread(target=run_hot_reload_server, daemon=True)
    hot_reload_thread.start()
    return hot_reload_thread


if __name__ == "__main__":
    print(f"Page server starting in: {BASE_DIR}")

    # Show allowed files configuration from manifest.toml
    allowed_config = get_allowed_files()
    static_paths = allowed_config.get("static_paths", [])
    library_files = allowed_config.get("library_files", set())

    if static_paths:
        print("Static directories from manifest.toml:")
        for static_path in static_paths:
            print(f"  - {BASE_DIR}/{static_path}/ → /{static_path}/")

    if library_files:
        print("Library files from manifest.toml:")
        for lib_file in sorted(library_files):
            print(f"  - {BASE_DIR}/{lib_file} → /{lib_file}")

    if not static_paths and not library_files:
        print("No static paths or library files configured in manifest.toml")

    print(f"Template: {TEMPLATE_FILE}")

    # Setup hot reload file watcher
    file_watcher = setup_file_watcher()

    # Start hot reload server
    hot_reload_thread = start_hot_reload_server()

    try:
        app.run(host="0.0.0.0", port=5000, debug=False)
    finally:
        # Cleanup file watcher on exit
        if file_watcher:
            file_watcher.stop()
            file_watcher.join()
