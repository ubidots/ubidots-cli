import sys
import os

import docker
import requests
from flask import Flask
from flask import Response
from flask import request
from flask_cors import CORS

# Disable Flask's default static folder to prevent route conflicts
app = Flask(__name__, static_folder=None)

# Enable CORS for all routes
CORS(
    app,
    origins="*",
    allow_headers="*",
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
)

# Routing configuration from environment variables
ROUTING_MODE = os.environ.get("ROUTING_MODE", "path")  # "subdomain", "port", or "path"

try:
    docker_client = docker.from_env()
except Exception as e:
    print(f"Error connecting to Docker: {e}", file=sys.stderr)
    sys.exit(1)


def get_routes_from_docker():
    """Get page name → upstream mapping from Docker labels"""
    try:
        containers = docker_client.containers.list(
            filters={"label": "ubidots_cli_page=true"}
        )

        routes = {}
        for container in containers:
            subdomain = container.labels.get("page_subdomain")
            upstream = container.labels.get("page_upstream")

            if subdomain and upstream:
                if ROUTING_MODE == "path":
                    # For path routing, use page name (same as subdomain) as key
                    routes[subdomain] = upstream
                else:
                    # For subdomain routing, use subdomain as key
                    routes[subdomain] = upstream

        return routes
    except Exception as e:
        print(f"Error getting routes from Docker: {e}", file=sys.stderr)
        return {}


def determine_target_page():
    """Determine target page using subdomain, port, or path routing"""

    if ROUTING_MODE == "subdomain":
        # Subdomain routing: dashboard.localhost:8044 → dashboard
        host = request.headers.get("Host", "")
        subdomain = host.split(".")[0].split(":")[0]
        if subdomain and subdomain != "localhost":
            print(f"[ROUTING] Subdomain routing: {subdomain}", file=sys.stderr)
            return subdomain
        else:
            print("[ROUTING] No subdomain found", file=sys.stderr)
            return None

    elif ROUTING_MODE == "port":
        # Port routing mode: Flask manager should not be running
        print(
            "[ERROR] Flask manager should not be running in port routing mode",
            file=sys.stderr,
        )
        return None

    elif ROUTING_MODE == "path":
        # Path routing: localhost:8044/dashboard → dashboard
        path = request.path.strip("/")
        if path:
            # Extract first path segment as page name
            page_name = path.split("/")[0]
            print(
                f"[ROUTING] Path routing: /{page_name} (full path: {request.path})",
                file=sys.stderr,
            )
            return page_name
        else:
            print("[ROUTING] No path found", file=sys.stderr)
            return None

    print(f"[ROUTING] Unknown routing mode: {ROUTING_MODE}", file=sys.stderr)
    return None


def build_upstream_url_subdomain(upstream, request, path):
    """Build upstream URL for subdomain routing"""
    # For subdomain routing, forward path as-is
    if path:
        upstream_url = f"http://{upstream}/{path}"
    else:
        upstream_url = f"http://{upstream}/"
    return upstream_url


def build_upstream_url_path(upstream, request, path):
    """Build upstream URL for path routing"""
    # For path routing, remove the page name from the path before forwarding
    remaining_path = "/".join(request.path.strip("/").split("/")[1:])
    if remaining_path:
        # Forward the remaining path as-is
        # The page container will handle serving files from both root and /static/
        upstream_url = f"http://{upstream}/{remaining_path}"
    else:
        upstream_url = f"http://{upstream}/"
    return upstream_url


def build_upstream_url_port(upstream, request, path):
    """Build upstream URL for port routing"""
    # For port routing, forward path as-is (though this shouldn't be called)
    if path:
        upstream_url = f"http://{upstream}/{path}"
    else:
        upstream_url = f"http://{upstream}/"
    return upstream_url


def build_upstream_url(upstream, request, path):
    """Build upstream URL based on current routing mode"""
    if ROUTING_MODE == "subdomain":
        return build_upstream_url_subdomain(upstream, request, path)
    elif ROUTING_MODE == "path":
        return build_upstream_url_path(upstream, request, path)
    elif ROUTING_MODE == "port":
        return build_upstream_url_port(upstream, request, path)
    else:
        # Default to subdomain behavior
        return build_upstream_url_subdomain(upstream, request, path)


@app.route("/api/routes", methods=["GET"])
def list_routes():
    """List all registered routes"""
    routes = get_routes_from_docker()
    return {
        "routes": routes,
        "count": len(routes),
        "info": "Routes are based on subdomains (e.g., dashboard.localhost:8044)",
    }


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "manager": "flask-pages-manager",
        "routing": "subdomain-based",
    }


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def proxy(path=""):
    """Proxy requests using subdomain or port routing"""

    # Get Host header for logging
    host = request.headers.get("Host", "")
    print(f"[PROXY] Received request for Host: {host}, Path: /{path}", file=sys.stderr)

    # Determine target page using routing method
    target_page = determine_target_page()
    print(f"[DEBUG] Target page: {target_page}", file=sys.stderr)

    # Get routes from Docker labels
    routes = get_routes_from_docker()
    print(f"[DEBUG] Available routes: {routes}", file=sys.stderr)

    # If no target page found, show error
    if not target_page:
        error_msg = f"No page determined. Mode: {ROUTING_MODE}, Available: {list(routes.keys())}"
        print(f"[ERROR] {error_msg}", file=sys.stderr)
        return Response(error_msg, status=404)

    if target_page not in routes:
        error_msg = f"Page '{target_page}' not found. Available: {list(routes.keys())}"
        print(f"[ERROR] {error_msg}", file=sys.stderr)
        return Response(error_msg, status=404)

    upstream = routes[target_page]

    # Build upstream URL based on routing mode
    upstream_url = build_upstream_url(upstream, request, path)

    if request.query_string:
        upstream_url += f"?{request.query_string.decode()}"

    print(f"[PROXY] Routing {target_page} → {upstream_url}", file=sys.stderr)

    try:
        # Forward the request
        resp = requests.request(
            method=request.method,
            url=upstream_url,
            headers={k: v for k, v in request.headers if k.lower() != "host"},
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            timeout=30,
        )

        excluded_headers = [
            "content-encoding",
            "content-length",
            "transfer-encoding",
            "connection",
        ]
        headers = [
            (name, value)
            for (name, value) in resp.raw.headers.items()
            if name.lower() not in excluded_headers
        ]

        return Response(resp.content, status=resp.status_code, headers=headers)
    except requests.exceptions.RequestException as e:
        return {
            "error": "Failed to proxy request",
            "target_page": target_page,
            "upstream": upstream,
            "details": str(e),
        }, 502


if __name__ == "__main__":
    print("Flask Pages Manager starting...")
    print("Routing mode: SUBDOMAIN-based")
    print("Querying Docker for page containers...")
    routes = get_routes_from_docker()
    print(f"Found {len(routes)} registered pages:")
    for subdomain, upstream in routes.items():
        print(f"  - {subdomain}.localhost:8044 → {upstream}")
    app.run(host="0.0.0.0", port=8044, debug=False)
