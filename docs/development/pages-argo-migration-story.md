# Pages Dev Engine — Full Migration Story

> **Audience:** Any developer picking up this work for the first time, including someone who has never touched the Argo project.
>
> **Branch:** `back/SC-2277__migrate_pages_local_dev_backend_from_custom_docker_stack_to_argo_local_file_target`

---

## Table of Contents

1. [How the Pages Dev Engine Worked Before](#1-how-the-pages-dev-engine-worked-before)
2. [Why We Wanted to Replace It](#2-why-we-wanted-to-replace-it)
3. [What Argo Is and Why It Was the Right Choice](#3-what-argo-is-and-why-it-was-the-right-choice)
4. [The First Difficulty: No Compatible Argo Image](#4-the-first-difficulty-no-compatible-argo-image)
5. [Understanding master vs master_v2](#5-understanding-master-vs-master_v2)
6. [What Needed to Come from master into master_v2](#6-what-needed-to-come-from-master-into-master_v2)
7. [CLI Standardization: Commons Extraction](#7-cli-standardization-commons-extraction)
8. [Testing Process and Image Pipeline](#8-testing-process-and-image-pipeline)
9. [Decision Guide: When to Touch Argo vs When to Touch the CLI](#9-decision-guide-when-to-touch-argo-vs-when-to-touch-the-cli)
10. [What Remains](#10-what-remains)
11. [Key Files Reference](#11-key-files-reference)

---

## 1. How the Pages Dev Engine Worked Before

The old pages local dev stack depended on two Docker layers that the CLI orchestrated directly.

### Layer 1 — Flask Manager container

A single container named `flask-pages-manager` ran from the image `ubidots/pages-server:latest` on port `8044`. Its job was to act as a reverse proxy: on every incoming HTTP request, it called the Docker API to find the right upstream container, then proxied the request.

Key properties of this container:
- Mounted `/var/run/docker.sock` at runtime so it could call the Docker API.
- Ran `pip install flask requests docker flask-cors` on every container start — slow and required internet access.
- Performed a live Docker container lookup on every single request (no caching).

### Layer 2 — Per-page containers

For each page the developer started, the CLI spun up a dedicated Python container. These containers:
- Mounted the page project directory from the host.
- Served the page files via a custom Flask app.
- Ran a file watcher inside the container for hot-reload.
- Used the label `ubidots_cli_page` so the Flask Manager could discover them.
- Required the same `ubidots/pages-server` image to be built and maintained.

Teardown was complex: 2 containers + 1 network + 1 image per dev session, plus ~15 environment variables per page.

---

## 2. Why We Wanted to Replace It

The old stack had accumulated a set of structural problems:

| Problem | Impact |
|---|---|
| Docker socket mounted | Security surface on every dev machine |
| Docker API on every request | Latency; no route caching |
| `pip install` on every manager start | Slow startup; required internet |
| Bespoke `pages-server` image | Image to maintain, build, and push separately |
| Per-page containers | Resource cost; complex orchestration |
| The functions module already used Argo | Inconsistency between modules |

The functions module was already using Argo as its reverse proxy. Pages reusing the same Argo container would eliminate all of the above.

---

## 3. What Argo Is and Why It Was the Right Choice

Argo is a FastAPI-based gateway container. It runs two internal servers:

| Server | Port | Role |
|---|---|---|
| **Admin** (`main_admin.py`) | `8040` | REST API — register and delete route/target pairs |
| **Gateway** (`main_gateway.py`) | `8042` | HTTP proxy — routes requests to registered targets |

When a developer calls `functions dev start`, the CLI posts a route registration to the Admin API:

```
POST http://localhost:8040/api/_/route/
{ "path": "my-fn", "bridge": { "target": { "type": "rie_function", "url": "http://..." } } }
```

Requests to `http://localhost:8042/my-fn/...` are then proxied by the Gateway to the Lambda RIE container.

### Why pages could use the same container

Argo supports a `local_file` target type — instead of proxying to another server, it serves static files from a directory on disk. If the page workspace (`~/.ubidots_cli/pages/<workspace-key>/`) is volume-mounted into the Argo container, Argo can serve it directly. No per-page container, no Docker socket, no bespoke image.

The new pages architecture:

```
pages dev start
  → register route: POST /api/_/route/
    { "path": "<workspace-key>", "bridge": { "target": { "type": "local_file", "base_path": "/pages/<workspace-key>" } } }

Browser: GET http://localhost:8042/<workspace-key>/
  → Argo gateway looks up route → local_file target
  → serves ~/.ubidots_cli/pages/<workspace-key>/index.html from host filesystem
```

A `copy_watcher` subprocess watches the source directory and copies changed files to the workspace. A `hot_reload_server` subprocess watches the workspace and pushes SSE events to the browser when files change.

---

## 4. The First Difficulty: No Compatible Argo Image

When the migration work started, the Docker image in use was `ubidots/functions-argo:2.0.1`.

**Problem:** This image was built from the `master_v2` branch of Argo. `master_v2` does not include the `local_file` target type. `POST /api/_/route/` with `"type": "local_file"` would return a validation error.

The `master` branch of Argo _does_ have `local_file`. So the natural instinct was: build from `master`.

**Second problem:** `master` had **removed** the `rie_function` and `rie_function_raw` target types. These are what the functions module depends on. Building from `master` meant the functions module's route registrations would start returning 422 errors.

At this point there was no published image that supported both requirements simultaneously:

| Image | Built from | API match | `rie_function` | `local_file` |
|---|---|---|---|---|
| `2.0.1` | `master_v2` | No (CLI sends new API path) | Yes | No |
| `2.0.2` (interim) | `master` | Yes | No | Yes |
| **`2.0.3` (final)** | **`master_v2` (fixed)** | **Yes** | **Yes** | **Yes** |

The only path forward was to fix `master_v2` to be compatible with what the CLI sends, and to add `local_file` support to it.

---

## 5. Understanding master vs master_v2

These are two long-lived branches of the Argo project that diverged around March 2024 and have never been merged back together. Understanding why they differ is essential to knowing what to change and what to leave alone.

### master_v2 — the CLI-specific branch

`master_v2` was created specifically so the CLI's `functions dev start` could run Argo as a self-contained Docker container with no external services.

Key properties:
- **Database:** SQLite via `aiosqlite` — no external PostgreSQL required
- **ORM:** SQLModel
- **Data model:** Single flat `Adapter` table (route + target stored together as JSON)
- **Admin API path:** `POST /adapter/` (original, now fixed)
- **Middleware scope key:** `scope["adapter"]`
- **Target types:** `rie_function`, `rie_function_raw`, `raw`, `aws_lambda`, `raw_function`, `static`
- **No migrations:** uses `SQLModel.metadata.create_all` on startup

The "no external dependencies" design is intentional and must be preserved. The container must start without a PostgreSQL server.

### master — the production branch

`master` is the full production Argo codebase. It has been significantly refactored since the `master_v2` divergence point.

Key properties:
- **Database:** PostgreSQL via `asyncpg`
- **ORM:** Pure SQLAlchemy (SQLModel removed)
- **Data model:** Split `ArgoRoute` + `ArgoBridge` tables
- **Admin API path:** `POST /api/_/route/`
- **Middleware scope key:** `scope["argo_bridge"]`
- **Target types:** `aws_lambda`, `raw_function`, `raw`, `static`, `local_file`, `mcp_lambda`
- **Migrations:** Alembic

### Where the CLI-Argo mismatch came from

When the pages migration work began, the CLI code had already been aligned with `master`'s API:
- `ARGO_API_BASE_PATH = "api/_/route"` — `master`'s path
- The registration payload used a `bridge`-nested structure — `master`'s payload shape

But the running Docker image (`2.0.1`) was built from `master_v2`, which still used the old `/adapter/` path and a flat payload. **The CLI and the image were not talking the same language.** This mismatch was silent: registrations appeared to succeed but the routes were never stored correctly, so functions were unreachable.

---

## 6. What Needed to Come from master into master_v2

The investigation identified three surgical changes to `master_v2` — nothing that touches the database engine, no infrastructure changes. The detailed implementation plan is at:

```
/home/inumaki/Desktop/temp-cli/argo/docs/superpowers/plans/2026-04-08-cli-api-alignment.md
```

### Task 1 — Fix the admin API path

**Files changed:** `argo/api/router.py`, `argo/api/adapter/router.py`

`master_v2` had `APIRouter(prefix="/api/v2")` on the outer router and `APIRouter(prefix="/adapter")` on the inner router — resulting in `POST /api/v2/adapter/`.

Changed to `prefix="/api/_"` and `prefix="/route"` — resulting in `POST /api/_/route/`.

Committed as `fcac234` on `master_v2`.

### Task 2 — Accept the bridge-nested CLI payload

**Files changed:** `argo/adapter/schemas.py`, `argo/api/adapter/router.py`

The CLI sends:
```json
{
  "path": "my-fn",
  "label": "my-fn",
  "is_strict": true,
  "middlewares": [],
  "bridge": {
    "label": "my-fn",
    "target": { "type": "rie_function", "url": "http://..." }
  }
}
```

The old `POST /` handler accepted `AdapterCreate` (flat schema), which had no `bridge` field. Pydantic silently ignored the `bridge` key and stored the adapter with `target=None`.

Two new schemas were added to `argo/adapter/schemas.py`:

```python
class BridgeIn(SQLModel):
    label: LabelStr | None = None
    target: TargetType

class AdapterCreateFromBridge(SQLModel):
    label: LabelStr | None = None
    path: PathStr
    is_strict: bool = True        # defaults to True (not None)
    middlewares: list[MiddlewareType] | None = None
    bridge: BridgeIn
```

The `POST /` handler was updated to accept `AdapterCreateFromBridge`, unwrap `bridge.target`, and create the flat `AdapterCreate` internally before persisting.

Committed as `0a7d8f3` on `master_v2`.

### Task 3 — Add the `local_file` target type

**Files changed:** `argo/target/__init__.py`
**Files created:** `argo/target/local_file.py`

The `local_file.py` file was copied from `origin/master` with one adjustment: `master` uses `request.scope["argo_route"]` to get the route, but `master_v2`'s middleware stores the route at `scope["adapter"]`. That one line was changed.

The `LocalFileTarget` was added to the `TargetType` union in `argo/target/__init__.py`.

Committed as `e1203a3` on `master_v2`.

### Additional fix — `nest-asyncio` in main dependencies

**File changed:** `pyproject.toml` in the Argo project

Both `main_gateway.py` and `main_admin.py` import `nest_asyncio` when `DEBUG=True` (the default). The image build uses `poetry install --without dev`. `nest_asyncio` was in the dev dependency group — so it was excluded from the built image, causing a `ModuleNotFoundError` crash on container startup.

Fix: moved `nest-asyncio` from `[tool.poetry.group.dev.dependencies]` to `[tool.poetry.dependencies]`.

Committed as `d74a48b` on `master_v2`.

After all four changes, the image was rebuilt and pushed as `randomgenericusername/functions-argo:2.0.3`.

---

## 7. CLI Standardization: Commons Extraction

As part of this migration, code that was duplicated between the functions and pages modules was extracted into a shared `cli/commons/` package. This work happened in the same branch as the pages migration.

### Problem before extraction

The functions module (`cli/functions/`) had its own hardcoded Argo constants scattered across `cli/functions/engines/settings.py` and `cli/commons/helpers.py`. The pages module was about to need the same constants. Two modules using the same Argo container, with constants defined in two places, would immediately drift.

### What was extracted

**`cli/commons/settings.py`** — single source of truth for all Argo/Docker constants:

```python
HUB_USERNAME = "randomgenericusername"   # TODO: update once published to ubidots hub
ARGO_VERSION = "2.0.3"
ARGO_IMAGE_NAME = f"{HUB_USERNAME}/functions-argo:{ARGO_VERSION}"
ARGO_CONTAINER_NAME = "argo"
ARGO_LABEL_KEY = "ubidots_cli_argo"
ARGO_HOSTNAME = "ubi.argo"
ARGO_API_BASE_PATH = "api/_/route"
ARGO_INTERNAL_ADAPTER_PORT = "8040/tcp"
ARGO_INTERNAL_TARGET_PORT = "8042/tcp"
ARGO_EXTERNAL_ADAPTER_PORT = 8040
ARGO_EXTERNAL_TARGET_PORT = 8042
HOST_BIND = "127.0.0.1"
```

**`cli/commons/engines/docker/container.py`** — `BaseDockerContainerManager`: label-based `get()`/`list()`, shared `start()`/`logs()`/`restart()`, abstract `stop()`.

**`cli/commons/engines/docker/network.py`** — `BaseDockerNetworkManager`: shared `get()`/`list()`, abstract `create()`.

**`cli/commons/engines/docker/client.py`** — `BaseDockerClient`: abstract factory for all four manager types.

Both `cli/functions/engines/docker/` and `cli/pages/engines/docker/` now extend these base classes. Module-specific behavior (e.g., `FunctionDockerContainerManager` translating `ContainerNotFoundError` to `ContainerNotFoundException`) is added as overrides.

**`cli/commons/helpers.py`** — `argo_container_manager()` and `verify_and_fetch_images()` moved here so both modules can call them.

### Pages pipeline alignment with functions

The functions module had `GetImageNamesStep` and `ValidateImageNamesStep` in its pipeline to pull and verify Docker images before starting. The pages module had no equivalent — it would silently fail if the Argo image was missing locally.

Two new steps were added to all pages dev pipelines (`cli/pages/pipelines/dev_engine.py`):
- `GetArgoImageNameStep` — resolves `ARGO_IMAGE_NAME` from commons settings
- `ValidateArgoImageStep` — calls `PageDockerValidator` to pull/verify the image

These steps are inserted before `EnsureArgoRunningStep` in every pages executor (`cli/pages/executor.py`).

---

## 8. Testing Process and Image Pipeline

### The two validation gates

Before any code change can be considered done, two commands must pass without error from the project root:

```bash
# 1. Linting + type checking
make validate     # runs ruff check, ruff format, mypy

# 2. Test suite
poetry run pytest
```

In the `testing/` directory, end-to-end testing of the actual CLI commands is also required. The `testing/` directory contains a pre-created function project. From inside it:

```bash
cd testing
poetry run ubidots functions dev start   # must exit 0 with no error
```

For pages, from a page project directory:
```bash
poetry run ubidots pages dev start       # must exit 0, Argo route registered
```

### Building and pushing the Argo image

Always work on and build from the `master_v2` branch:

```bash
cd /home/inumaki/Desktop/temp-cli/argo
git checkout master_v2

# After making changes:
poetry lock

# Build (produces argo2:<version> locally via buildah)
bash scripts/build_image.sh

# Load into Docker daemon
buildah push argo2:2.0.3 docker-daemon:randomgenericusername/functions-argo:2.0.3

# Push to hub (requires docker login)
docker push randomgenericusername/functions-argo:2.0.3

# Remove local cache so the CLI pulls fresh on next run
docker rmi randomgenericusername/functions-argo:2.0.3
```

After pushing, update `ARGO_VERSION` in `cli/commons/settings.py` if the version changed.

### Verifying the image manually

After pushing a new image, verify the API before updating the CLI version constant:

```bash
# Pull the image into a test container
docker run -d --name argo-test \
  -p 8040:8040 -p 8042:8042 \
  randomgenericusername/functions-argo:2.0.3

# Verify admin API is up and returns empty list
curl -s http://localhost:8040/api/_/route/ | python3 -m json.tool
# Expected: []

# Register a test route (bridge-nested payload)
curl -s -X POST http://localhost:8040/api/_/route/ \
  -H "Content-Type: application/json" \
  -d '{"path":"test","label":"test","is_strict":false,"middlewares":[],"bridge":{"label":"test","target":{"type":"local_file","base_path":"/tmp","allowed_extensions":[".html"]}}}' \
  | python3 -m json.tool
# Expected: 200 with target.type == "local_file"

# Clean up
docker rm -f argo-test
```

### Errors encountered and how to diagnose them

**`ModuleNotFoundError: No module named 'nest_asyncio'`** — the image was built without `nest_asyncio` in the main dependencies. Go to the Argo `master_v2` branch, move `nest-asyncio` from `[tool.poetry.group.dev.dependencies]` to `[tool.poetry.dependencies]`, rebuild the image.

**`422 Unprocessable Entity` on `pages dev start`** — the payload shape sent to Argo doesn't match what the server expects. Check that `register_page_in_argo()` in `cli/pages/engines/helpers.py` sends the bridge-nested payload (not a flat one). Check that the running container has the correct image version (the 2.0.3 image accepts bridge-nested; older images do not).

**`404 Not Found` on route registration** — the admin API path is wrong. The correct path is `POST http://localhost:8040/api/_/route/` (note trailing slash). Verify `ARGO_API_BASE_PATH = "api/_/route"` in `cli/commons/settings.py`.

**`BaseDockerContainerManager.__init__() got an unexpected keyword argument`** — a dataclass subclass is missing the `@dataclass` decorator. All Docker manager classes that add fields must be decorated with `@dataclass`.

**`Server disconnected without sending a response`** — the Argo container crashed immediately after starting. Check container logs: `docker logs argo`. The most common cause is a missing Python dependency that is only in dev deps.

---

## 9. Decision Guide: When to Touch Argo vs When to Touch the CLI

This question comes up often because both the Argo project and the CLI need to be in sync. Use this table:

| Symptom / Task | Where to fix | What to change |
|---|---|---|
| New target type needed (e.g., `grpc_function`) | **Argo `master_v2`** | Create `argo/target/new_type.py`, add to `TargetType` union in `argo/target/__init__.py`, rebuild image |
| CLI sends wrong payload shape (422 from admin API) | Usually **CLI** | Fix `register_page_in_argo()` or `get_argo_input_adapter()` to match what Argo expects |
| Argo doesn't understand the payload the CLI sends | **Argo `master_v2`** | Add or update the schema in `argo/adapter/schemas.py` and handler in `argo/api/adapter/router.py`, rebuild image |
| Admin API path mismatch (404) | **Argo `master_v2`** if Argo changed paths; **CLI** if CLI has wrong constant | Fix `argo/api/router.py` or `ARGO_API_BASE_PATH` in `cli/commons/settings.py` |
| Container crashes on startup | **Argo `master_v2`** | Diagnose from `docker logs argo`; fix missing deps, bad startup code, or broken migrations |
| New pipeline step for pages/functions dev | **CLI** | Add a `PipelineStep` subclass in `cli/pages/pipelines/dev_engine.py` or `cli/functions/pipelines.py` |
| Docker image pull fails (Hub) | **CLI** `cli/commons/settings.py` | Update `HUB_USERNAME`, `ARGO_VERSION`, `ARGO_IMAGE_NAME` after pushing new image |
| Argo starts but gateway returns wrong status | **Argo `master_v2`** | Debug middleware (`argo/middleware/argo.py`) or target handler |
| New Argo constant needed in CLI | **CLI** `cli/commons/settings.py` | Add constant there; import it where needed |

### The cardinal rule

**Never build the production image from `master`.** The `master` branch requires PostgreSQL and Redis at runtime. The `master_v2` branch is self-contained (SQLite only). Always use `master_v2` as the build branch.

If `master` has something `master_v2` needs, port it surgically (as was done for Tasks 1–3 above). Do not change the database engine, do not add external service requirements.

---

## 10. What Remains

### On this CLI branch

- [ ] Verify `pages dev stop` works end-to-end after migration
- [ ] Verify `pages dev restart` works end-to-end
- [ ] Verify `pages dev list` shows correct status and source path
- [ ] Full manual smoke test (`pages dev start` → browser → hot-reload → `dev stop`)

### Constants to update after production image push

- [ ] `HUB_USERNAME` in `cli/commons/settings.py`: change from `"randomgenericusername"` to `"ubidots"` once the image is published under the `ubidots` Docker Hub account
- [ ] `ARGO_VERSION` in `cli/commons/settings.py`: update to the new version after each image rebuild
- [ ] `FUNCTIONS_HUB_USERNAME` in `cli/functions/pipelines.py` (line with `GetImageNamesStep`): currently `"ubidots"` because runtime images are already there; consolidate once both Argo and runtime images share the same hub account

### Pre-existing issues (not introduced by this branch)

- [ ] Pre-existing mypy errors in `cli/functions/commands.py` lines 273 and 325: type mismatches between `str` and `int`/`dict` — not related to this work

---

## 11. Key Files Reference

### CLI project (`/home/inumaki/Desktop/temp-cli/ubidots-cli`)

| File | Role |
|---|---|
| `cli/commons/settings.py` | Single source of truth: all Argo/Docker constants including image name, ports, API path |
| `cli/commons/helpers.py` | `argo_container_manager()` — start/reuse Argo container; `verify_and_fetch_images()` |
| `cli/commons/engines/docker/container.py` | `BaseDockerContainerManager` — shared Docker container logic |
| `cli/commons/engines/docker/network.py` | `BaseDockerNetworkManager` — shared Docker network logic |
| `cli/commons/engines/docker/client.py` | `BaseDockerClient` — abstract factory |
| `cli/commons/exceptions.py` | `ContainerNotFoundError`, `ContainerAlreadyRunningException` |
| `cli/pages/engines/helpers.py` | `register_page_in_argo()`, `deregister_page_from_argo()`, `get_pages_workspace()`, `render_index_html()`, `get_tracked_files()` |
| `cli/pages/engines/docker/image.py` | `PageDockerImageDownloader` — pulls Argo image |
| `cli/pages/engines/docker/validators.py` | `PageDockerValidator` — validates Argo image availability |
| `cli/pages/pipelines/dev_engine.py` | All pages dev step classes: `GetArgoImageNameStep`, `ValidateArgoImageStep`, `EnsureArgoRunningStep`, etc. |
| `cli/pages/executor.py` | Wires steps into executors for each pages dev command |
| `cli/functions/pipelines.py` | All functions step classes: `GetImageNamesStep`, `ValidateImageNamesStep`, `GetArgoContainerManagerStep`, etc. |
| `cli/functions/helpers.py` | `get_argo_input_adapter()` — builds functions bridge payload; re-exports `argo_container_manager`, `verify_and_fetch_images` |
| `cli/functions/engines/docker/container.py` | `FunctionDockerContainerManager` — extends base, translates exceptions |
| `cli/functions/engines/docker/network.py` | `FunctionDockerNetworkManager` — extends base |

### Argo project (`/home/inumaki/Desktop/temp-cli/argo`)

| File | Role |
|---|---|
| `argo/adapter/schemas.py` | `Adapter` (ORM model), `AdapterCreate`, `AdapterCreateFromBridge`, `BridgeIn` — the bridge-nested schema the CLI sends |
| `argo/api/adapter/router.py` | `POST /api/_/route/` handler — accepts `AdapterCreateFromBridge`, unwraps `bridge.target` |
| `argo/api/router.py` | Outer router — sets prefix `/api/_` |
| `argo/target/__init__.py` | `TargetType` union — all supported target types |
| `argo/target/local_file.py` | `LocalFileTarget` — serves static files from `base_path` (added for pages module) |
| `argo/target/rie_function.py` | `RieFunctionTarget` — HTTP POST to Lambda RIE container (functions module) |
| `argo/target/rie_function_raw.py` | `RieFunctionRawTarget` — variant for raw functions |
| `argo/middleware/argo.py` | `ArgoMiddleware` — looks up adapter and stores it at `scope["adapter"]` |
| `scripts/build_image.sh` | Two-stage buildah build: produces `argo2:<version>` locally |
| `pyproject.toml` | All dependencies; `nest-asyncio` must be in `[tool.poetry.dependencies]` (not dev) |

### Documentation

| File | Purpose |
|---|---|
| `docs/development/argo-integration-state.md` (this repo) | Current technical state: architecture diagrams, payload contract, known bugs, build instructions, what remains |
| `docs/development/pages-argo-migration-status.md` (this repo) | Detailed pages architecture: workspace layout, `index.html` generation, request flow, QA walkthrough |
| `docs/development/pages-argo-migration-story.md` (this file) | Full narrative: before/after, difficulties, what was ported, standardization work, decision guide |
| `argo/docs/development/master-v2-investigation.md` (Argo repo) | Full analysis of `master` vs `master_v2` divergence — read this before making any Argo changes |
| `argo/docs/superpowers/plans/2026-04-08-cli-api-alignment.md` (Argo repo) | Step-by-step implementation plan for the three alignment tasks applied to `master_v2` |
