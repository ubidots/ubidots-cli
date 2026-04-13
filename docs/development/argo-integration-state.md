# Argo Integration — State of the World

> Branch: `back/SC-2277__migrate_pages_local_dev_backend_from_custom_docker_stack_to_argo_local_file_target`
> Last updated: 2026-04-09

---

## What Argo Is

Argo is the shared local gateway that both the **functions** and **pages** dev-server commands depend on.
It runs as a single Docker container with two internal servers:

| Server | Default host port | Role |
|---|---|---|
| **Admin** (`main_admin.py`) | `8040` | REST API to register/delete routes |
| **Gateway** (`main_gateway.py`) | `8042` | HTTP proxy that routes incoming requests to registered targets |

The admin API path is `POST /api/_/route/` (constant `ARGO_API_BASE_PATH = "api/_/route"` in `cli/commons/settings.py`).

The image in use: `randomgenericusername/functions-argo:2.0.3` (placeholder hub; see TODO in `cli/commons/settings.py`).
Source project: `/home/inumaki/Desktop/temp-cli/argo` — **always build from the `master_v2` branch**.

---

## Architecture: How the CLI Uses Argo

### Shared container model

Both `functions dev start` and `pages dev start` share the same Argo container (`ARGO_CONTAINER_NAME = "argo"`).
`argo_container_manager()` in `cli/commons/helpers.py` is the single entry point — it starts the container if not running, restarts if paused/exited, and returns `(container, adapter_port, target_port)`.

The Argo container mounts `~/.ubidots_cli/pages/` at `/pages/` (read-only), which is where the pages workspace files live.

### Functions flow

```
functions dev start
  ├─ ValidateImageNamesStep       — docker pull argo image + runtime image
  ├─ GetClientStep                — Docker client
  ├─ GetNetworkStep               — create/reuse ubidots_cli_function_rie Docker network
  ├─ GetArgoContainerManagerStep  — start/reuse Argo container (argo_container_manager)
  ├─ GetFRIEContainerStep         — start AWS Lambda RIE container (the actual runtime)
  ├─ GetArgoContainerInputAdapterStep  — build bridge-nested registration payload
  ├─ CreateArgoContainerAdapterStep    — POST /api/_/route/ → register FRIE route in Argo
  └─ ... print URL, watch logs
```

The registered Argo route target type is `rie_function` or `rie_function_raw`.
The function is then reachable at `http://localhost:8042/{label}`.

### Pages flow

```
pages dev start
  ├─ GetArgoImageNameStep         — resolve ARGO_IMAGE_NAME from commons
  ├─ ValidateArgoImageStep        — docker pull argo image
  ├─ EnsureArgoRunningStep        — start/reuse Argo container (argo_container_manager)
  ├─ ComputeWorkspaceKeyStep      — stable hash: "<page_name>-<8hex>"
  ├─ GetPageWorkspaceStep         — ~/.ubidots_cli/pages/<workspace_key>/
  ├─ CopyTrackedFilesStep         — copy body.html, manifest.toml, assets → workspace
  ├─ RenderIndexHtmlStep          — render index.html with hot-reload snippet
  ├─ FindHotReloadPortStep        — pick a free port for the SSE reload server
  ├─ RegisterPageInArgoStep       — POST /api/_/route/ → register local_file route
  ├─ StartHotReloadSubprocessStep — launch hot-reload SSE server subprocess
  └─ StartCopyWatcherStep         — watch source dir, sync changes to workspace
```

The registered Argo route target type is `local_file` with `base_path=/pages/<workspace_key>`.
The page is reachable at `http://localhost:8042/<workspace_key>/`.

---

## Argo Registration Payload Contract

Both modules use the **bridge-nested** payload shape for `POST /api/_/route/`:

```json
{
  "path": "<route-path>",
  "label": "<unique-label>",
  "is_strict": false,
  "middlewares": [],
  "bridge": {
    "label": "<unique-label>",
    "target": {
      "type": "local_file | rie_function | rie_function_raw",
      ...target-specific fields
    }
  }
}
```

- `is_strict=false` for pages (sub-paths must resolve, e.g. `/workspace-key/app.js`)
- `is_strict=true` for functions (exact path match)
- The admin API unwraps `bridge.target` before writing to the `Adapter` table

Deregistration: `DELETE /api/_/route/~<label>` (tilde-prefix = lookup by label).

---

## Commons Standardization (this branch)

All Argo/Docker constants are now in `cli/commons/settings.py` (single source of truth):

```python
HUB_USERNAME = "randomgenericusername"   # TODO: update once published to ubidots hub
ARGO_VERSION = "2.0.3"                   # TODO: update on each image release
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

Shared base classes in `cli/commons/engines/docker/`:
- `BaseDockerContainerManager` — label-based `get()`/`list()`, shared `start()`/`logs()`/`restart()`, abstract `stop()`
- `BaseDockerNetworkManager` — shared `get()`/`list()`, abstract `create()`
- `BaseDockerClient` — abstract factory for all four managers

Both `cli/functions/engines/docker/` and `cli/pages/engines/docker/` extend these bases.

`verify_and_fetch_images()` moved to `cli/commons/helpers.py` and re-exported from `cli/functions/helpers.py`.

---

## Current Status

### Working

| Feature | Status |
|---|---|
| `functions dev start` | ✅ Working |
| `functions dev stop` | ✅ Working |
| `functions dev logs` | ✅ Working |
| `functions dev invoke` | ✅ Working |
| Argo image pulled on dev start | ✅ Working |
| Runtime image pulled on dev start | ✅ Working |
| Shared Argo container | ✅ Working |
| Commons constants / base classes | ✅ Implemented |

### Broken / Not Yet Complete

| Feature | Status | Details |
|---|---|---|
| `pages dev start` | ❌ 422 on Argo registration | See bug #1 below |
| `pages dev stop` | ❓ Untested after migration | Needs end-to-end verification |
| `pages dev restart` | ❓ Untested after migration | Needs end-to-end verification |
| `pages dev list` | ❓ Untested after migration | Needs end-to-end verification |
| Argo `master_v2` branch | ✅ Aligned and image rebuilt | All 4 fixes applied, image pushed |

---

## Known Bugs

### Bug #1 — `pages dev start` returns 422 Unprocessable Entity

**Symptom:**
```
poetry run ubidots pages dev start
> [ERROR]: Client error '422 Unprocessable Entity' for url 'http://localhost:8040/api/_/route/'
```

**Root cause:**
The Argo `POST /api/_/route/` endpoint (`AdapterCreateFromBridge`) requires the `bridge` key wrapping the target. The pages module's `register_page_in_argo()` in `cli/pages/engines/helpers.py` **is sending the correct bridge-wrapped payload** (fixed in this branch). However, the running Argo image (`randomgenericusername/functions-argo:2.0.3`) built from the `master` branch already supports this — so if you're getting this error, the container has a stale DB or a route conflict.

**What was wrong in this branch (now fixed):** An earlier incorrect edit flattened the bridge structure. It has been restored to bridge-wrapped format matching what the Argo API requires.

**If you still see 422:** Check whether the workspace key already exists in Argo's DB (`GET http://localhost:8040/api/_/route/~pages-<workspace_key>`). A 409 Conflict becomes a 422 in some error paths.

### Bug #2 — Argo image `randomgenericusername/functions-argo:2.0.3` crashed on startup (FIXED)

**Was:** `ModuleNotFoundError: No module named 'nest_asyncio'`

**Root cause:** `nest_asyncio` was in dev dependencies only; the image build uses `--without dev`; but both `main_gateway.py` and `main_admin.py` import it when `DEBUG=True` (which is the default).

**Fix applied:** Moved `nest-asyncio` from `[tool.poetry.group.dev.dependencies]` to `[tool.poetry.dependencies]` in the Argo project `pyproject.toml`. Image rebuilt and pushed.

### Bug #3 — Pre-existing mypy errors in `cli/functions/commands.py` (not introduced by this branch)

Lines 273 and 325 have type mismatches (`str` vs `int`/`dict`). Pre-existing, not related to this work.

---

## Argo: master vs master_v2

There are **two active branches** of the Argo project. **The `master_v2` branch is the one that must always be used to build and ship the image.** If `master_v2` is missing something, port it from `master` — do not build from `master` directly.

### `master_v2` — canonical build branch ✅ (now fully aligned)

All three CLI alignment tasks have been applied and are committed:

| Commit | Change |
|---|---|
| `fcac234` | Fix admin API prefix from `/api/v2/adapter` to `/api/_/route` |
| `0a7d8f3` | Accept bridge-nested CLI payload on `POST /api/_/route/` |
| `e1203a3` | Add `local_file` target for pages module |
| `d74a48b` | Move `nest-asyncio` to main deps (required at runtime when `DEBUG=True`) |

Current state of `master_v2`:
- Admin path: `POST /api/_/route/` ✅
- Accepts bridge-nested payload (`AdapterCreateFromBridge`) ✅
- `local_file` target type supported ✅
- `scope["adapter"]` middleware key ✅
- `nest_asyncio` in main deps (not excluded at build time) ✅
- All 23 tests passing ✅
- Image built and pushed: `randomgenericusername/functions-argo:2.0.3` ✅

### `master` — reference only, do not build from

The `master` branch has the same API alignment but is the older codebase. It served as the reference for porting the three alignment fixes into `master_v2`. Do not build production images from it.

---

## Building and Pushing the Argo Image

**Always work on and build from the `master_v2` branch.**

The image is built with `buildah` (not `docker build`) and pushed via `docker push`:

```bash
cd /home/inumaki/Desktop/temp-cli/argo
git checkout master_v2

# 1. Make your changes to the Argo source
# 2. Update version in pyproject.toml if needed
# 3. Update poetry.lock
poetry lock

# 4. Build the image (produces argo2:<tag> locally via buildah)
bash scripts/build_image.sh

# 5. Load into Docker daemon (needed for docker push)
buildah push argo2:2.0.3 docker-daemon:randomgenericusername/functions-argo:2.0.3

# 6. Push via docker (requires docker login)
docker push randomgenericusername/functions-argo:2.0.3

# 7. Remove stale local Docker cache so CLI pulls the fresh image next run
docker rmi randomgenericusername/functions-argo:2.0.3
```

After pushing, update `ARGO_VERSION` in `cli/commons/settings.py` if the version changed.

### Build script notes
- Uses a two-stage buildah build: `python:3.12-bullseye` (builder) → `python:3.12-slim-bookworm` (runtime)
- Installs with `poetry install --without dev --no-root`; all runtime deps must be in `[tool.poetry.dependencies]`
- Virtual env at `/app/.venv`; PATH is set to include it
- `alembic upgrade head` runs at build time (SQLite DB migrations baked into image)
- Tagged as `argo2:<version>` locally; must be re-tagged before pushing to hub

---

## What Remains for Full Completion

### On this CLI branch (`back/SC-2277`)

- [ ] Verify `pages dev stop` works end-to-end after migration
- [ ] Verify `pages dev restart` works end-to-end
- [ ] Verify `pages dev list` shows correct status
- [ ] Manual smoke test `pages dev start` end-to-end (the 422 path fix is in place; needs runtime verification)
- [ ] Update `HUB_USERNAME` and `ARGO_VERSION` in `cli/commons/settings.py` once image is under the `ubidots` hub account

### On Argo `master_v2` branch

- [x] Task 1: Fix API prefix — commit `fcac234`
- [x] Task 2: Accept bridge-nested payload — commit `0a7d8f3`
- [x] Task 3: Add `local_file` target — commit `e1203a3`
- [x] Move `nest-asyncio` to main deps — commit `d74a48b`
- [x] All 23 tests passing
- [x] Image built from `master_v2` and pushed as `randomgenericusername/functions-argo:2.0.3`
- [x] Image verified: `GET /api/_/route/` → `[]`, `POST /api/_/route/` with bridge payload → 200

### Eventual (post-stabilization)

- [ ] Move `HUB_USERNAME` to `ubidots` once images are published under that account (remove TODO in `cli/commons/settings.py` and `cli/functions/pipelines.py`)
- [ ] Consolidate `FUNCTIONS_HUB_USERNAME = "ubidots"` (hardcoded in `GetImageNamesStep`) with commons once both Argo and runtime images are under the same hub account
- [ ] Address pre-existing mypy errors in `cli/functions/commands.py` lines 273 and 325

---

## Key Files Reference

| File | Purpose |
|---|---|
| `cli/commons/settings.py` | Single source of truth for all Argo/Docker constants |
| `cli/commons/helpers.py` | `argo_container_manager()`, `verify_and_fetch_images()` |
| `cli/commons/engines/docker/container.py` | `BaseDockerContainerManager` |
| `cli/commons/engines/docker/network.py` | `BaseDockerNetworkManager` |
| `cli/commons/engines/docker/client.py` | `BaseDockerClient` |
| `cli/commons/exceptions.py` | `ContainerNotFoundError`, `ContainerAlreadyRunningException`, `ContainerExecutionException` |
| `cli/pages/engines/helpers.py` | `register_page_in_argo()`, `deregister_page_from_argo()`, `get_pages_workspace()` |
| `cli/pages/engines/docker/image.py` | `PageDockerImageDownloader` |
| `cli/pages/engines/docker/validators.py` | `PageDockerValidator` |
| `cli/pages/pipelines/dev_engine.py` | All pages dev step classes including `GetArgoImageNameStep`, `ValidateArgoImageStep` |
| `cli/functions/pipelines.py` | All functions step classes including `GetImageNamesStep`, `ValidateImageNamesStep` |
| `cli/functions/helpers.py` | `get_argo_input_adapter()`, re-exports `argo_container_manager`, `verify_and_fetch_images` |
| `argo/argo/adapter/schemas.py` | `AdapterCreateFromBridge`, `BridgeIn` (Argo project) |
| `argo/argo/api/adapter/router.py` | `POST /api/_/route/` handler (Argo project) |
| `argo/argo/target/local_file.py` | `LocalFileTarget` — serves page workspace files (Argo project) |
| `argo/scripts/build_image.sh` | Buildah-based two-stage image build script |
| `argo/docs/superpowers/plans/2026-04-08-cli-api-alignment.md` | Full implementation plan for `master_v2` alignment |
