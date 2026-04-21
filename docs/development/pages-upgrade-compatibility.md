# Pages Dev Server — Upgrade Compatibility Analysis

**Question:** Will existing users need to recreate their pages when updating from the master CLI
(two-container Flask/Docker architecture) to the new CLI (Argo-based architecture)?

**Short answer:** No, existing page source directories are fully compatible and work transparently
with `dev start` under the new CLI. However, there are specific edge cases that require user
action, particularly if pages are still running under the old architecture at update time.

---

## 1. Architecture Comparison

### Old architecture (master branch)

State lives entirely inside **Docker containers**. No files are written to `~/.ubidots_cli/`.

| What | Where |
|---|---|
| "Is this page running?" | Docker: container `page-{name}` with `status == running` |
| Routing table | Docker labels on running containers: `page_subdomain`, `page_upstream`, `page_path` |
| Flask manager knows about pages via | Docker API query on every HTTP request: `containers.list(filters={"label": "ubidots_cli_page=true"})` |
| Page URL | `http://localhost:8044/{sanitized-name}` (Flask manager, path mode) |
| Network | `ubidots_cli_pages` (Docker bridge) |
| Per-page containers | `page-{name}`, label `ubidots_cli_page=true` |
| Proxy container | `flask-pages-manager`, port 8044, label `ubidots_cli_pages_manager=true` |
| `dev stop` behavior | Stops Docker container but does **not** remove it (`container.stop()`, no `container.remove()`) |

**On-disk state written by `dev add` (source directory only):**
- `manifest.toml` (user-editable; required files, libraries)
- `.manifest.yaml` (auto-generated; page name, type, remote ID)
- `body.html`, `script.js`, `style.css`, `static/` (template contents)

**No `~/.ubidots_cli/pages/`, no `.pid`, no `.watcher.pid`.**

Evidence: `cli/pages/engines/docker/container.py:stop()` only calls `container.stop()`. `cli/pages/engines/helpers.py` contains no `~/.ubidots_cli` writes. `cli/pages/pipelines/dev_engine.py` and `executor.py` on master contain zero references to home-directory paths.

---

### New architecture (migration branch)

State splits across **host filesystem** and **Argo's internal DB**.

| What | Where |
|---|---|
| "Is this page running?" | `.pid` file in source dir (hot_reload_server PID) + Argo route registered |
| Routing table | Argo DB (Postgres/SQLite in the `argo` container); route keyed by `workspace_key` |
| Page URL | `http://localhost:8042/{workspace-key}/` (Argo gateway) |
| Network | `ubidots_cli_pages` (same Docker bridge) |
| Argo container | `argo`, port 8042 (gateway), port 8040 (admin API) |
| Per-page containers | None |

**On-disk state written by `dev add` (new branch) — adds to source dir state above:**
- `~/.ubidots_cli/pages/{workspace-key}/` — workspace directory
- `~/.ubidots_cli/pages/{workspace-key}/.source_path` — absolute path to source dir

**Written by `dev start` — into workspace and source dir:**
- `~/.ubidots_cli/pages/{workspace-key}/index.html` — generated HTML
- `~/.ubidots_cli/pages/{workspace-key}/*.{html,js,css,...}` — copies of tracked source files
- `<source-dir>/.pid` — PID of `hot_reload_server` subprocess
- `<source-dir>/.watcher.pid` — PID of `copy_watcher` subprocess

Evidence: `cli/pages/pipelines/dev_engine.py` `CreateWorkspaceStep`, `StartHotReloadSubprocessStep`, `StartCopyWatcherStep`; `cli/pages/engines/helpers.py` `get_pages_workspace()`.

---

## 2. Source Directory Compatibility

The source directory format is **identical** between master and the migration branch. All three are verified by direct file diff:

| File | master required? | new branch required? | Format changed? |
|---|---|---|---|
| `manifest.toml` | ✅ `[page]`, `js_libraries`, `css_libraries` | ✅ Same | No |
| `.manifest.yaml` | ✅ `project:{name,label,createdAt,type}`, `page:{id,label,name}` | ✅ Same | No |
| `body.html` | ✅ | ✅ | No |
| `script.js` | ✅ | ✅ | No |
| `style.css` | ✅ | ✅ | No |
| `static/` | ✅ | ✅ | No |

Evidence: `cli/pages/models.py` `DashboardPageModel.get_required_toml_fields/files/directories()` is character-for-character identical on both branches. `PageProjectMetadata` struct is identical. `read_page_manifest()` in `cli/pages/helpers.py` is identical.

**Conclusion: An existing source directory from master passes every validation step of the new CLI without modification.**

---

## 3. Step-by-Step Trace: `dev start` on an Old Page with the New CLI

Given a page created on master (source dir has `manifest.toml`, `.manifest.yaml`, `body.html`, `script.js`, `style.css`, `static/`; no `.pid`, no workspace):

| Step | What it checks | Result for old page |
|---|---|---|
| `ValidatePageDirectoryStep` | `manifest.toml` exists | ✅ PASS |
| `ReadPageMetadataStep` | `.manifest.yaml` readable, valid format | ✅ PASS |
| `ValidatePageStructureStep` | `manifest.toml` required fields + files | ✅ PASS |
| `GetClientStep` | Docker/Podman available | ✅ PASS |
| `GetContainerManagerStep` | — | ✅ PASS |
| `GetPageNameStep` | `name` field in `.manifest.yaml` | ✅ PASS |
| `GetWorkspaceKeyStep` | Computes `{name}-{sha256[:8]}` from path | ✅ PASS — new key computed |
| `ValidatePageNotRunningStep` | `.pid` file exists? | ✅ PASS — no `.pid` on old page |
| `GetNetworkStep` | `ubidots_cli_pages` network exists? | ✅ PASS — network created by old CLI still exists |
| `GetArgoImageNameStep` | — | ✅ PASS |
| `ValidateArgoImageStep` | `ubidots/functions-argo:2.1.0` pullable | ✅ PASS — published |
| `EnsureArgoRunningStep` | Start/reuse Argo container | ✅ PASS |
| `CleanOrphanedPagesStep` | Scan `~/.ubidots_cli/pages/` | ✅ PASS — dir is empty or nonexistent |
| `CreateWorkspaceStep` | Create `~/.ubidots_cli/pages/{key}/` | ✅ PASS — creates it |
| `CopyTrackedFilesStep` | Copy files from source to workspace | ✅ PASS |
| `FindHotReloadPortStep` | Find free port ≥ 9000 | ✅ PASS |
| `RenderIndexHtmlStep` | Generate `index.html` from `manifest.toml` + `body.html` | ✅ PASS |
| `DeregisterPageFromArgoStep` | Remove stale Argo route (best-effort) | ✅ PASS — nothing to remove |
| `RegisterPageInArgoStep` | POST route to Argo | ✅ PASS |
| `StartCopyWatcherStep` | Launch `copy_watcher` subprocess | ✅ PASS |
| `StartHotReloadSubprocessStep` | Launch `hot_reload_server` subprocess | ✅ PASS |
| `StoreHotReloadPortStep` | Write `.pid` | ✅ PASS |
| `PrintPageUrlStep` | Print URL | ✅ PASS |

**Result: `dev start` on an old page succeeds end-to-end with the new CLI. No page recreation required.**

---

## 4. Edge Cases and Failure Modes

### 4.1 — Old page containers still running at update time

**Scenario:** User updates the CLI while `page-{name}` and `flask-pages-manager` containers are running.

**What breaks:** `dev stop` with the new CLI fails. `ValidatePageRunningStep` checks for a `.pid` file. No `.pid` exists for old pages. The step raises `PageIsAlreadyStoppedError` even though the Docker container is running.

Evidence: `cli/pages/pipelines/dev_engine.py` `ValidatePageRunningStep` — checks `pid_file = data["project_path"] / ".pid"`, raises if absent.

**Consequence:** The user cannot use `dev stop` to stop an old-architecture page. The old Docker container keeps running until killed manually.

**Resolution:** User must manually stop old containers before using the new CLI:
```bash
docker stop page-{name}
docker stop flask-pages-manager
```
After that, `dev start` with the new CLI works normally.

**No data loss.** Source files are untouched.

---

### 4.2 — Old stopped containers lingering in Docker

**Scenario:** User had stopped a page with the old CLI before updating. The old CLI's `stop()` method only stops the container, it does not remove it (`container.stop()` only, no `container.remove()`). The stopped `page-{name}` container still exists in Docker.

**What breaks:** Nothing in the new architecture. The new CLI never queries for `ubidots_cli_page=true` containers or `flask-pages-manager`. The new `dev start` on that page will create a fresh workspace, start Argo, and work correctly.

**Side effect:** Stopped containers accumulate in Docker. They are not cleaned up automatically by the new CLI. `dev clean` on the new branch only operates on `~/.ubidots_cli/pages/` workspaces — it has no knowledge of old Docker containers.

**Resolution:** User can manually remove them:
```bash
docker rm page-{name}
docker rm flask-pages-manager
```
Or they can leave them; they don't interfere.

---

### 4.3 — URL change (user-visible, unavoidable)

**Old URL pattern:** `http://localhost:8044/{sanitized-name}` (Flask manager port, path mode)  
**New URL pattern:** `http://localhost:8042/{page-name}-{8hex-hash}/` (Argo gateway port)

The hash is derived from the absolute path of the source directory:
```python
short = hashlib.sha256(str(page_dir_path.absolute()).encode()).hexdigest()[:8]
workspace_key = f"{page_name}-{short}"
```

Evidence: `cli/pages/engines/helpers.py` `compute_workspace_key()`.

**Consequence:** Any bookmarks, embedded URLs, iframe `src` attributes, or external links pointing to `localhost:8044/{name}` will break after upgrade. These must be updated to the new URL. The new URL is printed by `dev start` output.

**This is a breaking change for embedded/bookmarked local dev URLs, but not for page source files.**

---

### 4.4 — `dev list` shows nothing for old pages

**Scenario:** User runs `dev list` with the new CLI on a machine that only has old-architecture pages (no workspaces yet).

**What happens:** `ListAllPagesStep` scans `~/.ubidots_cli/pages/`. If the directory is empty or doesn't exist, it lists nothing. Old pages are invisible to `dev list` until the user runs `dev start` on each one (which creates the workspace).

Evidence: `cli/pages/pipelines/dev_engine.py` `ListAllPagesStep` — iterates `get_pages_workspace().iterdir()`, which is `~/.ubidots_cli/pages/`.

**No data loss.** Source directories are untouched. Once `dev start` is run, the page appears in `dev list`.

---

### 4.5 — `dev status` shows "stopped" for all old pages

**Scenario:** User runs `dev status` inside an old page directory with the new CLI.

**What happens:** `GetPageStatusStep` checks:
1. `.pid` file exists AND process alive (hot_reload_server) → absent for old pages
2. Argo has an active route for this `workspace_key` → no route registered yet

Both checks fail → status reported as `stopped`. This is correct: the page is not running under the new architecture.

Evidence: `cli/pages/pipelines/dev_engine.py` `GetPageStatusStep`.

---

### 4.6 — Flask manager container (port 8044) and Argo container (port 8042) coexist

**Scenario:** `flask-pages-manager` is still running when the new CLI starts Argo.

**What happens:** No conflict. They use different ports, different container names, different labels. `argo_container_manager()` only looks for a container named `"argo"` — it never interacts with `flask-pages-manager`.

Evidence: `cli/commons/helpers.py` `argo_container_manager()` — `client.client.containers.get(ARGO_CONTAINER_NAME)` where `ARGO_CONTAINER_NAME = "argo"` (from `cli/commons/settings.py`).

---

### 4.7 — Network name collision (`ubidots_cli_pages`)

Both architectures use `ubidots_cli_pages` as the Docker network name. The new CLI's `GetNetworkStep` calls `network_manager.list(names=["ubidots_cli_pages"])` and reuses the existing network if found.

**What happens:** The Argo container joins the existing `ubidots_cli_pages` network. Old stopped `page-{name}` containers remain on that network. No conflict — containers on the same network can coexist without communication issues if they aren't actively trying to reach each other.

Evidence: `cli/pages/engines/docker/network.py` `list()` uses `names=[page_engine_settings.CONTAINER.NETWORK.NAME]` where `NAME = "ubidots_cli_pages"`.

---

### 4.8 — `ubidots/pages-server:latest` image still exists on host

The old CLI's `dev add` attempts to build `ubidots/pages-server:latest` via `EnsureDockerImageStep`. The new CLI's `dev add` does not include `EnsureDockerImageStep` and never references this image.

**What happens:** The image just sits in Docker storage. It is not used and not removed. No conflict.

---

## 5. Summary Table

| Scenario | Pages need recreation? | Manual action required? | Data loss risk? |
|---|---|---|---|
| Old pages, never started | No | None — `dev start` works transparently | None |
| Old pages, previously stopped via old CLI | No | None — `dev start` works | None |
| Old pages currently running via old CLI | No | `docker stop page-{name} flask-pages-manager` before using new `dev stop` | None |
| Old stopped containers lingering | No | Optional: `docker rm page-{name}` for cleanup | None |
| URL bookmarks | N/A | Update to `localhost:8042/{name}-{hash}/` | N/A |
| `dev list` shows empty | No | Run `dev start` on each page to populate workspaces | None |

---

## 6. What the New CLI Does NOT Handle (Gaps)

These are not bugs — they are known omissions that affect the upgrade experience:

1. **No detection of old running containers.** If `page-{name}` is running when the user runs `dev start`, the new CLI silently ignores it. Two processes serve the same source files: the old Flask container on port 8044 and the new Argo route on port 8042. The user may not notice the old container is still running.

2. **No cleanup command for old Docker containers.** `dev clean` only removes orphaned workspaces in `~/.ubidots_cli/pages/`. There is no built-in command to remove `page-{name}` or `flask-pages-manager` containers from the old architecture.

3. **No upgrade notice in CLI output.** When `dev start` succeeds on an old page, it prints the new URL but says nothing about the old Flask manager being potentially still active or the URL having changed.

4. **`dev stop` fails on old-architecture running pages.** A user who updates the CLI while pages are running under the old architecture cannot use `dev stop` to stop them. The error message (`PageIsAlreadyStoppedError`) is misleading — the page IS running, just not in the new architecture's sense.

---

## 7. Recommended Pre-Merge Actions

The upgrade compatibility is fundamentally solid (no recreation needed, no data loss). The gaps above are UX issues that can be addressed without blocking the merge:

### Must-address before merge

None of the gaps above are blockers. The core upgrade path works.

### Recommended (improves user experience)

**A. Improve `dev stop` error message when `.pid` is absent**  
The current error says the page is "already stopped." After a CLI upgrade, the page might actually be running under the old architecture. A better message would acknowledge this possibility:

> "Page does not appear to be running (no .pid file found). If you recently updated the CLI and the page was running under the previous version, stop it with: `docker stop page-{name}`"

**B. Add upgrade notice to `dev start` output**  
When `dev start` completes successfully for a page that had no workspace before (i.e., `CreateWorkspaceStep` created a fresh workspace), print:

> "Note: The page URL has changed from `http://localhost:8044/...` to the URL above."

**C. Add a one-time cleanup note to `dev clean` output**  
When `dev clean` runs and finds no orphaned workspaces, optionally note that old-architecture Docker containers (if any) must be removed manually.

---

## 8. Evidence Index

All claims above are backed by specific code locations, verified by `git show` on both branches:

| Claim | Evidence location |
|---|---|
| Master: Docker container is the running-state record | `master:cli/pages/pipelines/dev_engine.py` `ValidatePageNotRunningStep`, `GetPageStatusTableStep` — all use `get_page_container()` + `container.status` |
| Master: stop does not remove container | `master:cli/pages/engines/docker/container.py:stop()` — calls `container.stop()` only |
| Master: no `~/.ubidots_cli/pages/` writes | `git show master:cli/pages/` — zero references to `home()`, `~/.ubidots_cli`, `.pid`, `.watcher.pid` |
| New branch: running-state = `.pid` file | `dev_engine.py:ValidatePageNotRunningStep` and `ValidatePageRunningStep` — check `project_path / ".pid"` |
| New branch: routing-state = Argo DB | `dev_engine.py:GetPageStatusStep` — queries `GET /api/_/route/` |
| Manifest formats identical | `cli/pages/models.py` `DashboardPageModel` — character-for-character identical on both branches |
| `.manifest.yaml` format identical | `cli/pages/helpers.py:read_page_manifest()` — identical on both branches |
| Workspace key formula | `cli/pages/engines/helpers.py:compute_workspace_key()` — `sha256(absolute_path)[:8]` |
| Old page `dev start` trace succeeds | Step-by-step analysis in Section 3 — every step either passes unconditionally or has a known-good outcome for old page state |
| Network name same | `master:cli/pages/engines/settings.py` `ContainerSettings.NETWORK_NAME = "ubidots_cli_pages"` == `new:cli/pages/engines/settings.py` `NetworkSettings.NAME = "ubidots_cli_pages"` |
| Flask manager and Argo use different ports | Master: port 8044; new: ports 8040/8042 (`cli/commons/settings.py`) |
| `dev list` scans workspace dir | `new:cli/pages/pipelines/dev_engine.py:ListAllPagesStep` — `workspace.iterdir()` only |
| `dev clean` does not touch old containers | `new:cli/pages/pipelines/dev_engine.py:CleanOrphanedPagesStep` — `shutil.rmtree(page_dir)` on workspace dirs only |
