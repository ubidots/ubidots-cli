# Pages Module — Argo Migration: Status & Context

**Branch:** `back/SC-2277__migrate_pages_local_dev_backend_from_custom_docker_stack_to_argo_local_file_target`
**Last updated:** 2026-04-21

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
12. [Manual QA Walkthrough](#12-manual-qa-walkthrough)

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
└── .copy_watcher.log    # stdout/stderr of copy_watcher subprocess
```

This workspace is **volume-mounted into the Argo container** at `/pages/`. Argo's `local_file` target reads files from `/pages/<workspace-key>/` to serve HTTP requests.

### index.html generation

At `dev start`, the CLI generates `index.html` from the source files and writes it directly to the workspace. It is never served from the source directory. The generation process:

1. Reads `manifest.toml` and `body.html` from the source directory
2. Loads CDN URLs from `settings.PAGES.TEMPLATE_PLACEHOLDERS` based on the page type
3. Renders the full HTML through the Ubidots page template engine
4. Injects a hot-reload + error-forwarding snippet before `</body>`:

```javascript
window.onerror = function(m, s, l, c) {
    fetch('http://localhost:<port>/__dev/error', { method: 'POST', ... });
};
window.onunhandledrejection = function(e) { ... };
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
| Argo container (`ubidots/functions-argo:2.1.0`) | Shared with functions. Serves static files via `local_file` target. Admin API on `127.0.0.1:8040`; gateway on `127.0.0.1:8042`. Pages workspace mounted at `/pages/` (read-only). |
| `~/.ubidots_cli/pages/<workspace-key>/` | Host workspace. Volume-mounted into Argo at `/pages/<workspace-key>/`. |
| `copy_watcher` subprocess | Watches source directory. Copies tracked files to workspace on change. PID written to `<source>/.watcher.pid`. Logs to `<workspace>/.copy_watcher.log`. |
| `hot_reload_server` subprocess | SSE server on port 9000. Watches workspace for changes. Pushes reload event to browser. PID written to `<source>/.pid`. Logs to `<workspace>/.hot_reload.log`. |
| `index.html` (generated) | Written to workspace at `dev start`. Injects CDN URLs and SSE reload script. Never overwritten by copy_watcher. |

### Container lifecycle

| Operation | What happens |
|---|---|
| `dev add` | Create source directory from template → save `manifest.toml` → compute workspace key → create workspace directory |
| `dev start` | Validate source dir → ensure Argo running (shared) → clean orphaned pages → create workspace (idempotent) → copy tracked files → render `index.html` → deregister stale route (best-effort) → register `local_file` adapter → start `copy_watcher` → start `hot_reload_server` → store hot-reload port |
| `dev stop` | Kill `hot_reload_server` → kill `copy_watcher` → deregister adapter from Argo → (Argo stays running for other pages/functions) |
| `dev restart` | Validate page is running → full stop → full start |
| `dev status` | Read Argo ports if container already running (never starts Docker) → query Argo for active routes → check for `.pid` file |
| `dev list` | Scan `~/.ubidots_cli/pages/` for workspace directories |
| `dev logs` | Tail both `.copy_watcher.log` and `.hot_reload.log` from workspace (whichever exist) |

### Argo registration (current — 2.1.0 API)

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
            "allowed_extensions": [".html", ".js", ".css", ".toml", ".json",
                                    ".png", ".svg", ".ico", ".woff", ".woff2",
                                    ".map", ".txt", ".md"]
        }
    }
}

DELETE http://localhost:8040/api/_/route/~pages-<workspace-key>
```

---

## 4. Key Decisions and Assumptions

**Shared Argo container:** Pages and functions share the same Argo container. The pages workspace root (`~/.ubidots_cli/pages/`) is volume-mounted at `/pages/` inside the container. Each page gets its own subdirectory under that mount. Functions containers connect via Docker internal DNS — no conflict.

**`copy_watcher` vs direct mount:** The source directory is NOT mounted into Argo. Only the workspace is. The copy_watcher bridges source → workspace on every file change. This decoupling serves two purposes: the workspace key (used as the Argo route path) is independent of the source directory name, and the CLI can inject generated files (`index.html`) into the workspace without any risk of polluting the source.

**`local_file` target type:** Introduced in the Argo project via [PR #137](https://bitbucket.org/ubidots/argo/pull-requests/137). Serves static files from a host directory mounted into the container. Present in `ubidots/functions-argo:2.1.0`.

**Workspace key stability:** The key is a hash of the absolute source path, not the directory name. Moving a page directory breaks the workspace association (a new key is computed and a new workspace is created). Renaming requires `dev stop` first, then `dev add` in the new location.

**Hot-reload file detection:** The hot_reload_server watches the workspace (not the source). Any change to a non-internal file triggers a reload. This is intentional: the workspace only ever contains files placed there by `copy_watcher` or by the CLI itself (`index.html`, internal dotfiles). Any change to a non-internal file is by definition a tracked-file change.

---

## 5. Argo Image Situation

### Current image

The CLI uses `ubidots/functions-argo:2.1.0` (constant `ARGO_IMAGE_NAME` in `cli/commons/settings.py`). This image includes:
- `local_file` target (`argo/target/local_file.py`)
- Admin API at `/api/_/route/` (changed from `/api/v2/adapter/` in `2.0.1`)
- Bridge-nested payload format (`ArgoRoute` + `ArgoBridge` data model)
- `is_strict` SQL bug fix

### Image source

Built from the Argo repo on branch `back/SC-2277__ubidots-cli-migrate-pages-to-use-argo-gateway` using `buildah` via `scripts/build_image.sh`. The image is **already published** to Docker Hub as `ubidots/functions-argo:2.1.0` — no local build is required.

### API differences from 2.0.1

| | `2.0.1` | `2.1.0` (current) |
|---|---|---|
| Admin API path | `/api/v2/adapter/` | `/api/_/route/` |
| Payload shape | flat `{path, target: {...}}` | nested `{path, bridge: {target: {...}}}` |
| Delete path | `/api/v2/adapter/~<label>` | `/api/_/route/~<label>` |
| Gateway scope key | `scope["adapter"]` | `scope["argo_route"]` |
| Data model | single `Adapter` | `ArgoRoute` + `ArgoBridge` (split) |
| `local_file` target | not present | present |

---

## 6. What Was Implemented

### Migration commit (`935aff8`)
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

### CodeRabbit review commits (`d402752`, `5173527`)
Additional fixes and cleanup in response to code review:
- Various improvements to error handling, naming, and code clarity across the migration

### All 11 post-migration bug fixes
All 11 fixes were applied as part of the migration or immediately after. **All are DONE:**

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

**`scope["adapter"]` vs `scope["argo_route"]`:** The design assumed the CLI would run against the current Argo source. The `2.0.1` image uses a different middleware scope key (`scope["adapter"]`). A proper image build from current source removes this divergence — `2.1.0` uses `scope["argo_route"]`.

**`is_strict` SQL bug:** Not anticipated in the plan. The `2.0.1` image has a bug where `not cls.model.is_strict` produces broken SQL (`0 = 1`), making non-strict prefix routes never match sub-paths. Already fixed in current source and `2.1.0`.

**Architecture docs are stale:** ✅ Fixed — `docs/development/architecture.md` and `docs/development/modules.md` have been updated to reflect the Argo + copy_watcher + hot_reload_server architecture.

---

## 8. Next Steps

In order of priority:

### Step 1 — Merge Argo PR #137 into `master_v2` ⚠️ Blocking

The Argo branch (`back/SC-2277__ubidots-cli-migrate-pages-to-use-argo-gateway`) is 2 commits ahead of `master_v2` with PR #137 open. This is the only remaining blocker before the CLI branch can be merged. The `2.1.0` image is already published — once the PR merges, `master_v2` will match what shipped.

### Step 2 — Manual QA walkthrough ⚠️ Not yet confirmed

The full walkthrough in Section 12 has not been confirmed as executed on the current code. This must be completed before merging the CLI branch.

### Step 3 — Merge PR1 then PR2

The original migration branch has been split into two PRs for reviewability:

- **PR1** (`back/SC-2277__pages-argo-pr1`) — additive only: new infrastructure (`copy_watcher`, `hot_reload_server`, workspace helpers, commons changes). Old architecture still functional. Merge first.
- **PR2** (`back/SC-2277__pages-argo-pr2`) — the switch: pipeline rewired, old Flask/Docker templates deleted, tests and docs. Merge after PR1.

### PR3 — Cleanup (post-merge)

- **Remove `--profile` from `dev add` and other local dev commands.** The `--profile` option on `dev add` only makes sense for remote API interactions (plan validation). Local dev commands (`dev add`, `dev start`, `dev stop`, `dev restart`, `dev status`, `dev list`, `dev logs`, `dev clean`) do not need a profile — they operate entirely on local state. `dev add` currently accepts `--profile` but this should be removed. Audit all local dev commands for similar stale options before opening PR3.
- Consolidate `FUNCTIONS_HUB_USERNAME = "ubidots"` (hardcoded in `GetImageNamesStep` in `cli/functions/pipelines.py:851`) with `HUB_USERNAME` in `cli/commons/settings.py` — currently both are `"ubidots"` so this is cosmetic.
- Address pre-existing mypy errors in `cli/functions/commands.py` lines 273 and 325.

---

## 9. Progress Tracker

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | Migrate pages dev engine to Argo | ✅ Done | Commit `935aff8` |
| 2 | All 11 post-migration bug fixes | ✅ Done | All verified in code |
| 3 | CodeRabbit review comments addressed | ✅ Done | Commits `d402752`, `5173527` |
| 4 | Fix `argo_container_manager` unpack (functions) | ✅ Done | Part of migration |
| 5 | Update CLI to use new Argo API (`/api/_/route/`) | ✅ Done | `ARGO_API_BASE_PATH = "api/_/route"` in `cli/commons/settings.py` |
| 6 | Update CLI to use bridge payload format | ✅ Done | `register_page_in_argo` sends `bridge`-wrapped payload |
| 7 | Orphaned page route cleanup | ✅ Done | `CleanOrphanedPagesStep` + `DeregisterPageFromArgoStep` wired into start pipeline |
| 8 | Fix broken pages engine tests | ✅ Done | All 15 tests in `test_helpers.py` pass; 24 new tests in `test_dev_engine_steps.py` |
| 9 | Update architecture/modules docs | ✅ Done | `architecture.md` and `modules.md` updated |
| 10 | CLI uses `ubidots/functions-argo:2.1.0` | ✅ Done | `ARGO_VERSION = "2.1.0"`, `HUB_USERNAME = "ubidots"` in `cli/commons/settings.py` |
| 11 | Argo PR #137 merged into `master_v2` | ⏳ Pending | PR open, 2 commits ahead of `master_v2` — only remaining code blocker |
| 12 | `ubidots/functions-argo:2.1.0` published to registry | ✅ Done | Available on Docker Hub |
| 13 | Manual QA walkthrough (Section 12) | ✅ Done | Executed 2026-04-21 on `back/SC-2277__pages-argo-pr2`. All commands pass. See Section 12 for full results. |

---

## 10. Current Runtime Status

The CLI branch is code-complete. All pipeline steps are implemented, all 11 post-migration bugs are fixed, and 59 tests across 5 test files cover the new engine. `ubidots/functions-argo:2.1.0` is published to Docker Hub.

**Remaining blocker:** Argo PR #137 must be merged into `master_v2` before the CLI branch can merge.

Manual QA completed 2026-04-21 on `back/SC-2277__pages-argo-pr2` (CLI v1.0.1, image `ubidots/functions-argo:2.1.0`). All local dev commands pass end-to-end. See Section 12 for the full results.

Working commands (QA confirmed): `dev add`, `dev start`, `dev stop`, `dev restart`, `dev status`, `dev list`, `dev logs`, `dev clean`. Cloud commands (`push`, `pull`, `list`, `get`, `add`, `delete`, `update`) use the Ubidots REST API and are unaffected by this migration.

---

## 11. Argo Image

`ubidots/functions-argo:2.1.0` is published to Docker Hub. Docker pulls it automatically when `pages dev start` or `functions dev start` is run for the first time — no manual build step required.

The image was built from the Argo repo (`back/SC-2277__ubidots-cli-migrate-pages-to-use-argo-gateway`) using `scripts/build_image.sh` (buildah). It includes `local_file` support, the `/api/_/route/` API prefix, bridge payload support, and all bug fixes.

---

## 12. Manual QA Results

**Executed:** 2026-04-21
**Branch:** `back/SC-2277__pages-argo-pr2`
**CLI version:** 1.0.1
**Argo image:** `ubidots/functions-argo:2.1.0`

**Note on hot-reload browser test (B5):** The SSE endpoint at `http://localhost:9000/__dev/reload` was verified to be up and responding. Full browser reload-on-edit was not verified in this automated run — manual browser verification is recommended.

**Note on interactive `dev clean` prompt (I1):** The interactive path (no `--yes`/`-y` flag, user answers the prompt) was not tested in this automated run. `--yes` and `-y` were both verified. The "No orphaned pages found." message path was also verified.

**Note on Argo GET response format:** The `GET /api/_/route/` response returns `target` directly at the top level rather than nested under `bridge`. This is how Argo serializes routes on read — the `bridge` wrapper is an internal concept. The routes register and serve correctly regardless.

| Section | Test | Result |
|---|---|---|
| A1 | `dev add` default name | ✅ |
| A2 | `dev add --name smoke-qa` | ✅ Source dir + workspace created |
| A3 | `dev add -v` / `--verbose` | ✅ Pipeline steps visible |
| A4 | `dev add` fails inside page dir | ✅ Exit 1, clear error |
| A5 | `dev add` fails if dir exists | ✅ Exit 1, clear error |
| B1 | `dev start` → URL printed | ✅ `http://localhost:8042/smoke-qa-9750937b/` |
| B2 | Argo route registered (`local_file` target) | ✅ Route present with correct label and base_path |
| B3 | Page returns 200 | ✅ |
| B4 | Static asset returns 200 | ✅ `script.js` served correctly |
| B5 | Hot-reload SSE endpoint up | ✅ `/__dev/reload` responds (browser test not automated) |
| B6 | `dev stop` exits 0 | ✅ |
| B7 | Argo route deregistered after stop | ✅ Label absent from route list |
| C1 | `dev status` while running shows URL | ✅ |
| C2 | `dev status -v` / `--verbose` shows steps | ✅ |
| C3 | `dev status` while stopped shows `stopped` | ✅ |
| C4 | `dev status` fails outside page dir | ✅ Exit 1, clear error |
| D1 | `dev list` while running shows URL + path | ✅ |
| D2 | `dev list -v` / `--verbose` shows steps | ✅ |
| D3 | `dev list` while stopped shows `stopped` | ✅ |
| D4 | Two pages running simultaneously both shown | ✅ Both routes in Argo, both rows in list |
| E1 | `dev logs` shows copy_watcher + hot_reload lines | ✅ |
| E2 | `dev logs --tail 3` / `-n 3` | ✅ Both forms work |
| E3 | `dev logs --follow` / `-f` streams, exits on timeout | ✅ Exit 124 (SIGKILL), no crash |
| E4 | `dev logs -v` / `--verbose` shows steps | ✅ |
| E5 | `dev logs` fails outside page dir | ✅ Exit 1, clear error |
| F1 | `dev restart` while running | ✅ Stops and restarts cleanly |
| F2 | Argo route re-registered after restart | ✅ `local_file` route present after restart |
| F3 | `dev restart -v` / `--verbose` shows steps | ✅ |
| F4 | `dev restart` fails when stopped | ✅ Exit 1, "already stopped" error |
| F5 | `dev restart` fails outside page dir | ✅ Exit 1, clear error |
| G1 | `dev start` when already running | ✅ Exit 1, error includes URL |
| G2 | `dev stop` when not running | ✅ Exit 1, "already stopped" error |
| G3 | `dev stop` outside page dir | ✅ Exit 1, clear error |
| G4 | `dev start` outside page dir | ✅ Exit 1, clear error |
| G5 | `dev restart` outside page dir | ✅ Exit 1, clear error |
| H | Crash recovery — stale Argo route | ✅ `dev start` clears stale route and starts cleanly |
| I2 | `dev clean --yes` removes orphan, no prompt | ✅ |
| I3 | `dev clean -y` removes orphan | ✅ |
| I4 | `dev clean` with no orphans prints message | ✅ "No orphaned pages found." |
| I5 | `dev clean -v` / `--verbose` shows steps | ✅ |
| J | Function + page share Argo simultaneously | ✅ Both routes present; stopping page leaves function intact |

