# Pages Module — Argo Migration: Status & Context

**Branch:** `back/migration_to_argo`
**Last updated:** 2026-04-06

---

## Table of Contents

1. [Previous Implementation (Replaced)](#1-previous-implementation-replaced)
2. [What a Page Is](#2-what-a-page-is)
3. [New Architecture (Argo-Based)](#3-new-architecture-argo-based)
4. [Key Decisions and Assumptions](#4-key-decisions-and-assumptions)
5. [Argo Image Situation](#5-argo-image-situation)
6. [What Was Implemented](#6-what-was-implemented)
7. [What Differs from the Original Plan](#7-what-differs-from-the-original-plan)
8. [Next Steps](#8-next-steps)
9. [Progress Tracker](#9-progress-tracker)
10. [Current Runtime Status](#10-current-runtime-status)
11. [Argo Image Build Instructions](#11-argo-image-build-instructions)

---

## 1. Previous Implementation (Replaced)

The old pages local dev stack used two Docker layers:

**Flask Manager container** (`flask-pages-manager`, image `ubidots/pages-server:latest`, port `8044`):**
- Reverse proxy that, on every HTTP request, called the Docker API to list running containers labelled `ubidots_cli_page`, found the right upstream, and proxied the request.
- Mounted `/var/run/docker.sock` at runtime for Docker introspection.
- Ran `pip install flask requests docker flask-cors` on every start (slow, required internet).

**Per-page containers** (one per running page, label `ubidots_cli_page`):
- Mounted the page project directory and served it via a custom Flask app.
- Required a custom `ubidots/pages-server` Docker image to be built and maintained.
- Ran hot-reload via a file watcher inside the container.

**Why it was replaced:**
- Docker API query on every single HTTP request — no caching.
- `pip install` on every manager container start.
- Docker socket mounted (security surface).
- Bespoke image to maintain.
- ~15 environment variables per page.
- Complex teardown: 2 containers + 1 network + 1 image per dev session.
- The functions module was already using Argo as a reverse proxy; pages reusing it eliminated all of the above.

---

## 2. What a Page Is

A page is a local directory with a fixed structure that the CLI understands and serves via Argo during development.

### Source directory structure

```
my-page/
├── manifest.toml        # user-editable: name, type, libraries, static paths
├── body.html            # page body markup
├── script.js            # main JS entry point
├── style.css            # main stylesheet
├── static/              # static assets (images, fonts, extra JS/CSS)
│   └── ...
├── .manifest.yaml       # auto-generated: remote page ID, sync state
├── .pid                 # written by dev start: hot_reload_server PID
└── .watcher.pid         # written by dev start: copy_watcher PID
```

`manifest.toml` is the developer-facing config file for the page. It declares every asset the page needs. The `[page]` section supports:

```toml
[page]
description = "My page"
keywords    = "sensor,dashboard"
static_paths = ["static"]          # local dirs/files copied to workspace recursively

js_libraries = [
    {src="script.js", type="module", defer="", crossorigin=""},
    {src="static/data.js", type="module"}
]
js_thirdparty_libraries = [        # CDN URLs — injected into <script> but NOT tracked
    {src="https://cdn.example.com/echarts.min.js"}
]

css_libraries = [
    {href="style.css", crossorigin=""}
]
css_thirdparty_libraries = [       # CDN URLs — injected into <link> but NOT tracked
    {href="https://fonts.googleapis.com/css2?family=Nunito&display=swap", type="font"}
]

link_thirdparty_libraries = [      # arbitrary <link> elements from CDN — NOT tracked
    {href="https://fonts.googleapis.com/css?family=Roboto&display=swap", type="font"}
]
```

At `dev start`, the CLI reads `manifest.toml` and `body.html` together and generates `index.html` in the workspace. Every entry in `js_libraries`, `css_libraries`, and `link_libraries` becomes a `<script>` or `<link>` tag in the generated HTML. The `*_thirdparty_*` variants work the same way in the HTML output, but their `src`/`href` values are remote URLs so no local file is tracked.

**Why `body.html` and `manifest.toml` are always tracked:** These are the two primary source files the developer edits. `body.html` is the inner HTML markup of the page. `manifest.toml` declares all the page's assets. Both are required to regenerate `index.html`. Any change to either must be reflected in the workspace immediately so the browser can reload with the latest content.

**Why `index.html` is excluded from copy tracking:** `index.html` does not exist in the source directory — it only exists in the workspace. It is assembled by the CLI at `dev start` from `manifest.toml` + `body.html` + CDN URLs from settings + the hot-reload SSE snippet. If copy_watcher were to copy an `index.html` from source to workspace it would overwrite the generated version and break the hot-reload injection. The exclusion is a guard: even if an `index.html` somehow ends up in the source directory, it is never copied.

### The workspace directory

At `dev add` (and idempotently at `dev start`), the CLI creates a workspace directory:

```
~/.ubidots_cli/pages/<workspace-key>/
```

The workspace key is derived from the page name and the absolute path of the source directory:

```python
def compute_workspace_key(page_name: str, page_dir_path: Path) -> str:
    raw = str(page_dir_path.absolute())
    short = hashlib.sha256(raw.encode()).hexdigest()[:8]
    return f"{page_name}-{short}"
```

The hash ensures that two pages with the same name in different directories get different workspace keys and never collide. The workspace contains:

```
~/.ubidots_cli/pages/<workspace-key>/
├── index.html           # generated by CLI at dev start (not copied from source)
├── body.html            # copied from source
├── manifest.toml        # copied from source
├── script.js            # copied from source
├── style.css            # copied from source
├── static/              # copied from source recursively
│   └── ...
├── .source_path         # written by CreateWorkspaceStep: absolute path to source dir
├── .hot_reload.log      # stdout/stderr of hot_reload_server subprocess
└── .copy_watcher.log    # stdout/stderr of copy_watcher subprocess (not yet implemented — see below)
```

This workspace is **volume-mounted into the Argo container** at `/pages/`. Argo's `local_file` target reads files from `/pages/<workspace-key>/` to serve HTTP requests.

### index.html generation

At `dev start`, the CLI generates `index.html` from the source files and writes it directly to the workspace. It is never served from the source directory. The generation process:

1. Reads `manifest.toml` and `body.html` from the source directory
2. Loads CDN URLs from `settings.PAGES.TEMPLATE_PLACEHOLDERS` based on the page type
3. Renders the full HTML through the Ubidots page template engine
4. Injects a hot-reload SSE snippet before `</body>`:

```javascript
var __s = new EventSource('http://localhost:<port>/__dev/reload');
__s.onmessage = function() { window.location.reload(); };
```

5. Sets `BASE_URL = /<workspace-key>` so all asset paths in the page resolve correctly under the Argo route prefix.

### How a request flows to the browser

```
Browser: GET http://localhost:8042/my-page-a1b2c3d4/
  → Argo gateway (port 8042)
  → ArgoMiddleware looks up route "my-page-a1b2c3d4" → local_file target
  → local_file strips route prefix → sub_path = "/index.html"
  → resolves /pages/my-page-a1b2c3d4/index.html  (inside container)
  → maps to ~/.ubidots_cli/pages/my-page-a1b2c3d4/index.html  (host)
  ← FileResponse
```

For a static asset:
```
Browser: GET http://localhost:8042/my-page-a1b2c3d4/static/data.js
  → local_file strips prefix → sub_path = "/static/data.js"
  → resolves /pages/my-page-a1b2c3d4/static/data.js
  ← FileResponse
```

### How file changes reach the browser

The `copy_watcher` subprocess watches the source directory using `watchdog`. When a tracked file changes:
1. The copy_watcher copies the file to the workspace
2. The `hot_reload_server` subprocess (a separate SSE server on port 9000) detects the change in the workspace
3. It pushes an SSE event to all connected browsers
4. The browser's `EventSource` handler calls `window.location.reload()`

The hot_reload_server watches for any file change in the workspace that is not in `_INTERNAL_FILES` (`index.html`, `.hot_reload.log`, `.copy_watcher.log`, `.source_path`). This is intentionally file-name-based, not extension-based, to handle dotfiles declared in `manifest.toml`.

---

## 3. New Architecture (Argo-Based)

Pages local dev now shares the **same Argo container** used by the functions module. There are no per-page Docker containers.

### Components

| Component | Role |
|---|---|
| Argo container (`ubidots/functions-argo:2.0.1-local-file`) | Shared with functions. Serves static files via `local_file` target. Admin API on `127.0.0.1:8040`; gateway on `127.0.0.1:8042`. Pages workspace mounted at `/pages/` (read-only). |
| `~/.ubidots_cli/pages/<workspace-key>/` | Host workspace. Volume-mounted into Argo at `/pages/<workspace-key>/`. |
| `copy_watcher` subprocess | Watches source directory. Copies tracked files to workspace on change. PID written to `<source>/.watcher.pid`. Logs to `<workspace>/.copy_watcher.log`. |
| `hot_reload_server` subprocess | SSE server on port 9000. Watches workspace for changes. Pushes reload event to browser. PID written to `<source>/.pid`. Logs to `<workspace>/.hot_reload.log`. |
| `index.html` (generated) | Written to workspace at `dev start`. Injects CDN URLs and SSE reload script. Never overwritten by copy_watcher. |

### Container lifecycle

| Operation | What happens |
|---|---|
| `dev add` | Create source directory from template → save `manifest.toml` → compute workspace key → create workspace directory |
| `dev start` | Validate source dir → ensure Argo running (shared) → create workspace (idempotent) → copy tracked files → render `index.html` → register `local_file` adapter → start `copy_watcher` → start `hot_reload_server` → store hot-reload port |
| `dev stop` | Kill `hot_reload_server` → kill `copy_watcher` → deregister adapter from Argo → (Argo stays running for other pages/functions) |
| `dev restart` | Validate page is running → full stop → full start |
| `dev status` | Read Argo ports if container already running (never starts Docker) → query Argo for active routes → check for `.pid` file |
| `dev list` | Scan `~/.ubidots_cli/pages/` for workspace directories |
| `dev logs` | Tail both `.copy_watcher.log` and `.hot_reload.log` from workspace (whichever exist) |

### Argo registration (current — 2.0.1 API)

```python
POST http://localhost:8040/api/v2/adapter/
{
    "path": "<workspace-key>",
    "label": "pages-<workspace-key>",
    "is_strict": False,
    "middlewares": [],
    "target": {
        "type": "local_file",
        "base_path": "/pages/<workspace-key>",
        "allowed_extensions": [".html", ".js", ".css", ".toml", ".json",
                                ".png", ".svg", ".ico", ".woff", ".woff2",
                                ".map", ".txt", ".md"]
    }
}

DELETE http://localhost:8040/api/v2/adapter/~pages-<workspace-key>
```

---

## 4. Key Decisions and Assumptions

**Shared Argo container:** Pages and functions share the same Argo container. The pages workspace root (`~/.ubidots_cli/pages/`) is volume-mounted at `/pages/` inside the container. Each page gets its own subdirectory under that mount. Functions containers connect via Docker internal DNS — no conflict.

**`copy_watcher` vs direct mount:** The source directory is NOT mounted into Argo. Only the workspace is. The copy_watcher bridges source → workspace on every file change. This decoupling serves two purposes: the workspace key (used as the Argo route path) is independent of the source directory name, and the CLI can inject generated files (`index.html`) into the workspace without any risk of polluting the source.

**`local_file` target type:** Introduced in the Argo project via [PR #127](https://bitbucket.org/ubidots/argo/pull-requests/127). Serves static files from a host directory mounted into the container. Not present in the official `2.0.1` image — see Section 5.

**Workspace key stability:** The key is a hash of the absolute source path, not the directory name. Moving a page directory breaks the workspace association (a new key is computed and a new workspace is created). Renaming requires `dev stop` first, then `dev add` in the new location.

**Hot-reload file detection:** The hot_reload_server watches the workspace (not the source). Any change to a non-internal file triggers a reload. This is intentional: the workspace only ever contains files placed there by `copy_watcher` or by the CLI itself (`index.html`, internal dotfiles). Any change to a non-internal file is by definition a tracked-file change.

---

## 5. Argo Image Situation

### Why the custom image exists

The official `ubidots/functions-argo:2.0.1` image does not support `local_file`. The `2.0.2` image is built locally from the Argo source until it is published to the registry. The Argo source (`/home/inumaki/Desktop/temp-cli/argo`) already contains everything needed — no patches required:
- `local_file.py` is already present and correct (introduced in [PR #127](https://bitbucket.org/ubidots/argo/pull-requests/127))
- `is_strict` SQL bug is already fixed (`cls.model.is_strict == False`)
- The middleware correctly sets `scope["argo_route"]` which `local_file.py` reads

Once `ubidots/functions-argo:2.0.2` is published to the registry, the local build becomes unnecessary and `ARGO_IMAGE_NAME` in `cli/commons/helpers.py` will just work as-is.

### API differences from 2.0.1

The Argo API changed significantly alongside the `local_file` addition:

| | `2.0.1` (old hack) | `2.0.2` (current) |
|---|---|---|
| Admin API path | `/api/v2/adapter/` | `/api/_/route/` |
| Payload shape | flat `{path, target: {...}}` | nested `{path, bridge: {target: {...}}}` |
| Delete path | `/api/v2/adapter/~<label>` | `/api/_/route/~<label>` |
| Gateway scope key | `scope["adapter"]` | `scope["argo_route"]` |
| Data model | single `Adapter` | `ArgoRoute` + `ArgoBridge` (split) |

### Current payload (2.0.2)

```python
POST http://localhost:8040/api/_/route/
{
    "path": "<workspace-key>",
    "label": "pages-<workspace-key>",
    "is_strict": False,
    "middlewares": [],
    "bridge": {
        "label": "pages-<workspace-key>",
        "target": {
            "type": "local_file",
            "base_path": "/pages/<workspace-key>",
            "allowed_extensions": [".html", ".js", ".css", ...]
        }
    }
}
```

### Test scripts

- `scripts/test_argo_local_file.sh` — tests a Docker image for `local_file` support. No argument tests `ubidots/functions-argo:2.0.2`.
- `scripts/test_argo_local_file_from_source.sh` — runs Argo directly from the source repo (spins up a throw-away Postgres container). Confirms the source has no bugs and `local_file` works correctly before any image is built.

---

## 6. What Was Implemented

### Migration commit (`07de8bf`)
The full pages dev engine was rewritten:

- `cli/pages/engines/helpers.py` — workspace helpers (`compute_workspace_key`, `get_page_workspace`, `get_tracked_files`, `render_index_html`, `register_page_in_argo`, `deregister_page_from_argo`)
- `cli/pages/engines/templates/copy_watcher.py` — new subprocess: watches source, copies tracked files to workspace on change
- `cli/pages/engines/templates/hot_reload_server.py` — new subprocess: SSE server on port 9000, watches workspace, pushes reload events to browser
- `cli/pages/pipelines/dev_engine.py` — new pipeline steps for all dev operations
- `cli/pages/executor.py` — updated all dev executors
- `cli/pages/pipelines/sync.py` — fixed `CreatePullDirectoryStep`
- `cli/settings.py` — new `PagesSettings` fields
- `cli/commons/helpers.py` — `argo_container_manager` shared between functions and pages; port utilities moved to commons
- Tests added in `cli/pages/tests/`

### Parity/cleanup commit (`ad16650`)
Four CLI surface fixes to align pages commands with the functions module:

- `pages update` — added `--new-label` option (mirroring `functions update`)
- `pages dev add` — removed non-functional `--remote-id` stub
- `functions dev logs` — removed `--profile/-p` (local command; profiles are irrelevant)
- `pages dev clean` — renamed `--confirm` to `--yes/-y`

### Unpack fix (`a025035`)
`GetArgoContainerManagerStep` in `cli/functions/pipelines.py` was only unpacking 2 values from `argo_container_manager()` which returns 3 (`container, adapter_port, target_port`). Fixed.

### All 11 post-migration bug fixes
All 11 fixes from `docs/superpowers/specs/2026-03-24-pages-dev-engine-fixes.md` were applied as part of the migration or immediately after. **All are DONE:**

| # | Fix | Status |
|---|-----|--------|
| 1 | `register_page_in_argo` silently ignores HTTP errors | ✅ Done — retries once, calls `raise_for_status()` |
| 2 | Hot-reload port fallback can collide with Argo ports | ✅ Done — `HOT_RELOAD_PORT_FALLBACK_START = 9001` in `PagesSettings` |
| 3 | Hot-reload watches by extension, misses dotfiles | ✅ Done — `_INTERNAL_FILES` set; any non-internal file triggers reload |
| 4 | `dev status` starts Docker/Argo as side-effect | ✅ Done — `TryGetArgoPortStep` never starts anything; handles `None` gracefully |
| 5 | Symlink check in `ValidatePageDirectoryStep` | ✅ Done — removed; only manifest check remains |
| 6 | Dead `render_index_html` in `cli/pages/helpers.py` | ✅ Done — removed |
| 7 | Unused `self._workspace` in `_ChangeHandler` | ✅ Done — removed |
| 8 | `CreatePullDirectoryStep` is a no-op | ✅ Done — creates dir, updates `data["project_path"]`; Extract/Save simplified |
| 9 | `dev restart` doesn't validate page is running | ✅ Done — `ValidatePageRunningStep` added to restart pipeline |
| 10 | `copy_watcher` schedules duplicate directory watchers | ✅ Done — single `recursive=True` observer on `source_dir` |
| 11 | `copy_watcher` re-copies files already copied at startup | ✅ Done — `--skip-initial-copy` flag; `StartCopyWatcherStep` always passes it |

---

## 7. What Differs from the Original Plan

**`scope["adapter"]` vs `scope["argo_route"]`:** The design assumed the CLI would run against the current Argo source. The `2.0.1` image uses a different middleware scope key (`scope["adapter"]`). The `local_file.py` injected into the custom image was adapted to use `scope["adapter"]` for compatibility. A proper image build from current source removes this divergence.

**`is_strict` SQL bug:** Not anticipated in the plan. The `2.0.1` image has a bug where `not cls.model.is_strict` produces broken SQL (`0 = 1`), making non-strict prefix routes never match sub-paths. Discovered at runtime, patched into the custom image. Already fixed in current source.

**Architecture docs are stale:** ✅ Fixed — `docs/development/architecture.md` and `docs/development/modules.md` have been updated to reflect the Argo + copy_watcher + hot_reload_server architecture.

---

## 8. Next Steps

In order of priority:

### Step 1 — Replace the custom Argo image ✅ Done

The `2.0.1-local-file` hack has been replaced. A proper `Dockerfile` now lives in the Argo repo root. Build locally with:

```bash
docker build -t ubidots/functions-argo:2.0.2 /path/to/argo/
```

The CLI has been updated to use `ubidots/functions-argo:2.0.2` and the new `/api/_/route/` API with bridge payload. Section 11 (manual rebuild instructions) is now obsolete.

### Step 2 — Orphaned page route cleanup ✅ Done

`CleanOrphanedPagesStep` wired into the `dev start` pipeline (runs silently with `confirm=True` after Argo is up). `DeregisterPageFromArgoStep` added before `RegisterPageInArgoStep` in the `dev start` pipeline to clear any stale route for the current page before re-registering.

### Step 3 — Fix broken pages engine tests ✅ Done

Patch target corrected from `cli.pages.engines.helpers.Path.home` to `cli.pages.engines.helpers.settings.CONFIG.DIRECTORY_PATH`. All 15 tests in `cli/pages/tests/engines/test_helpers.py` pass.

### Step 4 — Update architecture and module docs ✅ Done

`docs/development/architecture.md` and `docs/development/modules.md` updated. Pages sections now describe the Argo + workspace + copy_watcher + hot_reload_server architecture.

---

## 9. Progress Tracker

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | Migrate pages dev engine to Argo | ✅ Done | Commit `07de8bf` |
| 2 | All 11 post-migration bug fixes | ✅ Done | All verified in code |
| 3 | Pages command API parity with functions | ✅ Done | Commit `ad16650` |
| 4 | Fix `argo_container_manager` unpack (functions) | ✅ Done | Commit `a025035` |
| 5 | Custom Argo image built and working locally | ✅ Superseded | Replaced by item 6 |
| 6 | Build proper Argo image from source | ✅ Done | `ubidots/functions-argo:2.0.2` via `Dockerfile` in Argo repo |
| 7 | Update CLI to use new Argo API (`/api/_/route/`) | ✅ Done | Image constant, API paths, bridge payload — all updated |
| 8 | Orphaned page route cleanup | ✅ Done | `CleanOrphanedPagesStep` + `DeregisterPageFromArgoStep` wired into start pipeline |
| 9 | Fix broken pages engine tests | ✅ Done | Patch target corrected to `settings.CONFIG.DIRECTORY_PATH`; all 15 pass |
| 10 | Update architecture/modules docs | ✅ Done | `architecture.md` and `modules.md` updated to reflect Argo + copy_watcher + hot_reload_server |

---

## 10. Current Runtime Status

`pages dev start` works end-to-end on the current branch with the `ubidots/functions-argo:2.0.2` image built from source. Pages are served through Argo's gateway at `http://localhost:8042/<workspace-key>/`. Static assets load. Hot-reload fires on file changes.

Working commands: `dev add`, `dev start`, `dev stop`, `dev restart`, `dev status`, `dev list`, `dev logs`, `dev clean`, `push`, `pull`, cloud CRUD (`list`, `get`, `add`, `delete`, `update`).

---

## 11. Argo Image Build Instructions

The `ubidots/functions-argo:2.0.2` image is not yet published to the registry. Until it is, anyone setting up the dev environment must build it locally from the Argo source.

```bash
docker build -t ubidots/functions-argo:2.0.2 /home/inumaki/Desktop/temp-cli/argo/
```

The `Dockerfile` lives at the root of the Argo repo. It bundles Python 3.14, PostgreSQL, and Redis — no external services required at runtime. No patches are needed; the source already includes `local_file` support and all bug fixes.

---

## 12. Manual QA Walkthrough

Tests every command and option affected by this branch in a single top-to-bottom session.
Cloud CRUD commands (`pages list/get/add/delete/update/push/pull` and all `functions` cloud commands) are not included — they use the Ubidots REST API and are unaffected.

**Before starting:**
- Docker is running
- `ubidots/functions-argo:2.0.2` image is available locally (`docker images | grep argo`)
- CLI is installed from this branch
- A CLI profile is configured

Throughout this guide, `{key}` refers to the workspace key printed in the `dev start` output URL (format: `smoke-qa-XXXXXXXX`). Note it after step 2.

---

### Step 1 — Create a test page

From a temporary working directory:

```bash
ubidots pages dev add --name smoke-qa
```

Expected: exits 0, `smoke-qa/` directory created with `body.html`, `manifest.toml`, `script.js`, `style.css`, `static/`. A workspace at `~/.ubidots_cli/pages/smoke-qa-XXXXXXXX/` is also created.

The `--profile` option triggers plan validation on the remote server. If your profile has pages enabled:

```bash
ubidots pages dev add --name smoke-profile --profile <your-profile>
```

Expected: exits 0. If pages are not enabled on the plan, it exits non-zero with a clear error.

---

### Step 2 — Start the page

```bash
cd smoke-qa
ubidots pages dev start
```

Expected: exits 0. The output includes the page URL — note the workspace key from it (e.g. `http://localhost:8042/smoke-qa-ab12cd34/` → key is `smoke-qa-ab12cd34`).

Confirm the Argo route was registered with the new bridge payload:

```bash
curl -s http://localhost:8040/api/_/route/ | python3 -m json.tool
```

Expected: response contains an entry with `"label": "pages-{key}"` and `"target": {"type": "local_file", ...}` nested inside `"bridge"`. This confirms the new API path and payload structure are working.

Confirm the page is reachable through the gateway:

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8042/{key}/
```

Expected: `200`.

Also confirm that running `dev start` a second time fails — the page is already running:

```bash
ubidots pages dev start
```

Expected: exits non-zero with an error message about the page already running.

---

### Step 3 — Status while running

```bash
ubidots pages dev status
```

Expected: exits 0, output shows the page name, `running`, and the URL.

```bash
ubidots pages dev status -v
ubidots pages dev status --verbose
```

Expected: both exit 0. Output additionally shows each pipeline step as it executes (`(Starting OK)` / `(Finished OK)` lines). The result is the same status table.

---

### Step 4 — List while running

```bash
ubidots pages dev list
```

Expected: exits 0, output shows the page name, `running`, `http://localhost:8042/{key}/`, and the source directory path.

```bash
ubidots pages dev list -v
ubidots pages dev list --verbose
```

Expected: both exit 0 with the same table plus pipeline step output.

---

### Step 5 — Logs

```bash
ubidots pages dev logs
```

Expected: exits 0, output contains log lines from both the hot-reload server and the copy-watcher (look for `[hot-reload]` and `Copy-watcher started`).

```bash
ubidots pages dev logs --tail 5
ubidots pages dev logs -n 5
```

Expected: both exit 0, output has at most 5 lines. `-n` is the short form of `--tail` — both must work.

```bash
timeout 3 ubidots pages dev logs --follow; echo "exit: $?"
timeout 3 ubidots pages dev logs -f; echo "exit: $?"
```

Expected: both start streaming and are killed by the timeout. Exit code should be `0` or `124` (timeout). No crash or error message before the timeout. `-f` is the short form of `--follow`.

```bash
ubidots pages dev logs -v
ubidots pages dev logs --verbose
```

Expected: both exit 0 with pipeline step output visible.

---

### Step 6 — Restart

```bash
ubidots pages dev restart
```

Expected: exits 0. The page stops briefly and comes back up. Confirm the Argo route is re-registered:

```bash
curl -s http://localhost:8040/api/_/route/ | python3 -m json.tool
```

Expected: `pages-{key}` still present, proving the new deregister→register sequence works.

Test verbose and the restart-on-stopped guard:

```bash
ubidots pages dev restart -v
ubidots pages dev restart --verbose
```

Expected: both exit 0 with pipeline step output.

Now stop the page and confirm restart fails when it's not running:

```bash
ubidots pages dev stop > /dev/null
ubidots pages dev restart
```

Expected: exits non-zero with an error about the page not running. Start it again before continuing:

```bash
ubidots pages dev start
```

---

### Step 7 — Stop

```bash
ubidots pages dev stop
```

Expected: exits 0. Confirm the Argo route is gone:

```bash
curl -s http://localhost:8040/api/_/route/ | python3 -m json.tool
```

Expected: the array no longer contains `pages-{key}`. This confirms `deregister_page_from_argo` called the correct `DELETE /api/_/route/~pages-{key}` endpoint.

Confirm a second stop fails:

```bash
ubidots pages dev stop
```

Expected: exits non-zero.

Now test the verbose variants of stop (requires re-starting each time):

```bash
ubidots pages dev start
ubidots pages dev stop -v
ubidots pages dev start
ubidots pages dev stop --verbose
```

Expected: both exit 0 with pipeline step output.

---

### Step 8 — Status and list while stopped

```bash
ubidots pages dev status
```

Expected: exits 0, shows `stopped`, no URL in the output.

```bash
ubidots pages dev status -v
ubidots pages dev list
ubidots pages dev list -v
```

Expected: all exit 0. Status shows `stopped`. List shows the page with `stopped` status and no URL.

---

### Step 9 — Commands fail outside a page directory

```bash
cd /tmp
ubidots pages dev start
ubidots pages dev stop
ubidots pages dev restart
ubidots pages dev status
ubidots pages dev logs
```

Expected: every command exits non-zero with an error about not being in a page directory. Go back to the page directory after:

```bash
cd -
```

---

### Step 10 — Start after crash (stale Argo route)

This tests the `DeregisterPageFromArgoStep` added to the start pipeline.

Start the page, then simulate an unclean shutdown by killing processes directly without `dev stop`:

```bash
ubidots pages dev start
kill $(cat .pid) $(cat .watcher.pid)
rm .pid .watcher.pid
```

Confirm the stale Argo route is still registered (the crash didn't clean it up):

```bash
curl -s http://localhost:8040/api/_/route/ | python3 -m json.tool
```

Expected: `pages-{key}` is still in the list.

Now start again — this must succeed despite the stale route:

```bash
ubidots pages dev start
```

Expected: exits 0. `DeregisterPageFromArgoStep` deleted the stale route before registering a fresh one. Confirm the route is back:

```bash
curl -s http://localhost:8040/api/_/route/ | python3 -m json.tool
```

Expected: `pages-{key}` present again. Stop cleanly to end this step:

```bash
ubidots pages dev stop
```

---

### Step 11 — Orphan cleanup (`dev clean`)

Set up an orphaned workspace — a workspace whose source directory no longer exists:

```bash
mkdir -p ~/.ubidots_cli/pages/orphan-qa-deadbeef
echo "/nonexistent/path/that/does/not/exist" > ~/.ubidots_cli/pages/orphan-qa-deadbeef/.source_path
```

Run clean with `--yes` (skip prompt, non-interactive):

```bash
cd /tmp
ubidots pages dev clean --yes
```

Expected: exits 0, `orphan-qa-deadbeef/` workspace directory is gone. **No** `"No orphaned pages found."` message in the output — `--yes` suppresses it.

Re-create the orphan and test the `-y` short form:

```bash
mkdir -p ~/.ubidots_cli/pages/orphan-qa-deadbeef
echo "/nonexistent/path/that/does/not/exist" > ~/.ubidots_cli/pages/orphan-qa-deadbeef/.source_path
ubidots pages dev clean -y
```

Expected: same — exits 0, orphan removed, no "No orphaned" message.

Now run clean with no flags when there are no orphans left:

```bash
ubidots pages dev clean
```

Expected: exits 0, output contains `"No orphaned pages found."` — this is the interactive path where the message is shown.

Test verbose:

```bash
ubidots pages dev clean -v
ubidots pages dev clean --verbose
```

Expected: both exit 0 with pipeline step output.

---

### Step 12 — Functions dev start

Navigate to a valid function project directory (created with `ubidots functions dev add`):

```bash
cd /path/to/your-function
ubidots functions dev start
```

Expected: exits 0. Argo starts (or reuses the existing container — it is shared with pages). The function container starts and registers in Argo. The output shows the function URL.

Confirm the Argo route was registered using the new bridge payload and `/api/_/route/` endpoint:

```bash
curl -s http://localhost:8040/api/_/route/ | python3 -m json.tool
```

Expected: an entry with `"label": "{function-label}"` and a `"bridge"` object containing `"target": {"type": "http", ...}`.

Stop the function container and re-start with verbose to verify the option:

```bash
ubidots functions dev stop
ubidots functions dev start -v
ubidots functions dev stop
ubidots functions dev start --verbose
```

Expected: all start commands exit 0. `-v`/`--verbose` shows pipeline step output including the Argo registration step.

---

**Commands confirmed unaffected by this branch** — no changes to their pipelines, no Argo API calls added or modified:
`functions dev stop`, `functions dev restart`, `functions dev status`, `functions dev logs` (local), `functions dev clean`

