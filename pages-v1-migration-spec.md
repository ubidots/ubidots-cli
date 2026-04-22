# Pages V1 → Argo Migration: Spec & Implementation Plan

**Date:** 2026-04-21  
**Branch:** `back/SC-2277__migrate_pages_local_dev_backend_from_custom_docker_stack_to_argo_local_file_target`  
**Status:** Ready for implementation

---

## 1. Problem Statement

Users who have pages created and/or running under the old CLI (master branch, two-container Flask/Docker architecture) will update to the new CLI (Argo-based architecture) and expect everything to keep working. Without intervention:

- `dev list` shows nothing (no workspaces exist yet)
- `dev status` reports all pages as stopped even if Docker containers are running
- `dev stop` fails with a misleading "page not running" error on pages that are actively running under the old stack
- `dev logs` returns empty output (no workspace log files)
- `dev restart` and `dev start` on already-running old pages start a second instance

The root cause is that the old architecture stores all running state in Docker container metadata (labels, container status). The new architecture stores it on the host filesystem (`~/.ubidots_cli/pages/` workspaces, `.pid` files) and in Argo's internal DB. There is a one-time translation step needed.

**Goal:** Any `pages dev` command run after a CLI upgrade just works. The user notices nothing except a possible brief delay on the first command.

---

## 2. Context: Architecture Differences

### Old architecture (master)

| Concern | Mechanism |
|---|---|
| "Is page running?" | Docker container `page-{name}` with `status == running` |
| Routing table | Docker labels on containers: `page_subdomain`, `page_upstream`, `page_path` |
| Proxy | `flask-pages-manager` container, port 8044 |
| URL | `http://localhost:8044/{sanitized-name}` |
| On-disk per-page state | Source dir only: `manifest.toml`, `.manifest.yaml`, `body.html`, `script.js`, `style.css`, `static/` |
| `dev stop` | `container.stop()` — container kept, not removed |
| Network | `ubidots_cli_pages` Docker bridge |

No `~/.ubidots_cli/pages/` directory. No `.pid` or `.watcher.pid` files.

### New architecture (migration branch)

| Concern | Mechanism |
|---|---|
| "Is page running?" | `.pid` file in source dir (hot_reload_server PID) + Argo route registered |
| Routing table | Argo internal DB, route keyed by `workspace_key` |
| Proxy | `argo` container, port 8042 (gateway), port 8040 (admin) |
| URL | `http://localhost:8042/{name}-{8hex}/` |
| On-disk per-page state | Source dir (same as above) + `~/.ubidots_cli/pages/{key}/` workspace |
| `dev stop` | Kills subprocesses, deregisters Argo route |
| Network | `ubidots_cli_pages` (same name, reused) |

### Source directory compatibility

The source directory format (`manifest.toml`, `.manifest.yaml`) is **identical** between architectures. No source file migration is needed. Verified by direct diff of `cli/pages/models.py` and `cli/pages/helpers.py` on both branches.

---

## 3. Design

### 3.1 Trigger and Marker

A new pipeline step — `MigrateFromV1Step` — is injected as the **first step** in every `pages dev` executor function that interacts with local dev state:

- `start_local_dev_server`
- `stop_local_dev_server`
- `restart_local_dev_server`
- `show_local_dev_server_status`
- `list_local_pages`
- `clean_orphaned_pages`
- `logs_local_dev_server`

**Not** injected into: `dev add`, `dev push`, `dev pull`, or any cloud CRUD command. Those commands either don't need Docker or don't interact with local dev state.

**Marker file:** `~/.ubidots_cli/.pages_v1_migration_done`

On every invocation, `MigrateFromV1Step` checks for this file first. If present: return immediately (zero overhead — a single `Path.exists()` call). If absent: run migration. At the end of migration, write the marker.

The marker is written when Docker was available and all detectable pages were processed — even if some individual pages produced warnings. It is **never** written if Docker was unavailable. This ensures the migration retries on the next command that has a working Docker connection.

`MigrateFromV1Step` instantiates its own Docker client internally (via `PageEngineClientManager`) rather than relying on `data["client"]`, which has not been populated yet when this step runs first.

### 3.2 Detection

Scan Docker for all containers — regardless of status (running, stopped, exited, paused) — matching the filter:

```python
{"label": "ubidots_cli_page=true"}
```

This label (`LABEL_KEY = "ubidots_cli_page"` in `cli/pages/engines/settings.py`) was stamped on every per-page container by the old CLI.

From each container, read these labels:
- `page_path` — absolute path to the source directory on the host
- `page_subdomain` — the sanitized page name

Also query for the Flask manager: `containers.get("flask-pages-manager")`.

**A page is skipped (warning logged, migration continues) if:**
- `page_path` label is absent or empty
- `page_subdomain` label is absent or empty
- The directory at `page_path` does not exist on disk
- `manifest.toml` is not present in that directory

If no `ubidots_cli_page=true` containers exist at all: write marker and return. This is the common case for fresh installs and for users who already cleaned up their Docker state.

### 3.3 Per-Page Migration Logic

Migration calls the existing helper functions directly (`compute_workspace_key`, `register_page_in_argo`, `render_index_html`, `get_tracked_files`, `get_page_workspace`) rather than going through the `Pipeline` class. This keeps migration silent — no step-by-step output, no pipeline error-exit behavior that would abort other pages.

#### For all pages (running or stopped)

1. Compute workspace key:
   ```python
   workspace_key = compute_workspace_key(page_name, Path(page_path))
   ```
2. Create workspace directory: `~/.ubidots_cli/pages/{key}/` (idempotent — `mkdir(parents=True, exist_ok=True)`)
3. Write `.source_path`: absolute path to source dir

#### For stopped/exited/paused containers only

Stop here. The workspace now exists. `dev list` shows the page as stopped. `dev start` from the source directory works on first attempt without any further migration needed.

#### For running containers (additional steps)

4. Stop the old `page-{name}` container: `container.stop()`
5. Ensure Argo is running: call `argo_container_manager()` — starts it if needed, reuses if already running
6. Copy tracked files from source dir to workspace (same logic as `CopyTrackedFilesStep`: call `get_tracked_files()`, copy each to workspace)
7. Find a free hot-reload port starting at `settings.PAGES.HOT_RELOAD_PORT_DEFAULT`
8. Render `index.html` into workspace: call `render_index_html(source_dir, workspace_dir, hot_reload_port)`
9. Deregister any stale Argo route: call `deregister_page_from_argo(workspace_key, argo_admin_port)` (best-effort, suppresses exceptions)
10. Register new route: call `register_page_in_argo(workspace_key, argo_admin_port)`
11. Start `copy_watcher` subprocess — write `.watcher.pid` to source dir
12. Start `hot_reload_server` subprocess — write `.pid` to source dir

#### Flask manager cleanup

After all pages are processed: if the `flask-pages-manager` container exists and is running, and no `ubidots_cli_page=true` containers remain in running state, stop it.

### 3.4 Error Handling

**This section must be fully documented in code comments inside `MigrateFromV1Step.execute()` and in the migration log file. Every failure path must be observable.**

| Failure | Behaviour | Marker written? |
|---|---|---|
| Docker daemon unavailable | Skip silently, no output | No — retries on next command |
| Individual page: `page_path` label missing | Log warning to migration log, skip page | Yes (at end) |
| Individual page: source dir missing | Log warning to migration log, skip page | Yes (at end) |
| Individual page: workspace creation fails | Log warning to migration log, skip page | Yes (at end) |
| Individual page: Argo registration fails (running page) | Log warning, page ends up stopped with workspace created | Yes (at end) |
| Individual page: subprocess won't start (running page) | Log warning, deregister route if already registered, page ends up stopped | Yes (at end) |
| Old container stopped but restart fails mid-way | Workspace and any completed steps are kept; page ends up stopped; warning logged | Yes (at end) |
| Argo unavailable (image pull fails, daemon issue) | Create workspaces for all pages; skip restart for all running ones; all pages end up stopped | Yes (at end) |
| All pages processed with zero errors | Write marker, no output | Yes |
| All pages processed with some warnings | Write marker; if any warnings were logged, print one summary line: `"Migration completed with warnings. See ~/.ubidots_cli/.pages_v1_migration.log"` | Yes |

**Migration log file:** `~/.ubidots_cli/.pages_v1_migration.log`

Each warning entry is a single line:
```
[2026-04-21T14:32:01] WARN  page=my-page  reason="source directory not found at /home/user/pages/my-page"
[2026-04-21T14:32:01] WARN  page=sensor-dash  reason="Argo registration failed: connection refused"
```

The log is appended to, not overwritten, so it survives across multiple migration attempts (in case Docker was unavailable on the first try).

**Graceful degradation principle:** a running page that fails to restart under the new arch must always end up in a clean stopped state — workspace created, old container stopped. `dev start` from the source directory must always be sufficient to recover it.

### 3.5 Output

Migration is **silent by default**. No output is printed unless:
- Warnings were logged → print the one summary line pointing to the log file
- A running page was successfully migrated → no output (the subsequent command, e.g. `dev start`, will print its own success/URL output)

This satisfies the "zero extra steps, just works" requirement. Users who want to know what happened can inspect the log file.

---

## 4. New Files

| File | Purpose |
|---|---|
| `cli/pages/pipelines/migration.py` | `MigrateFromV1Step` class and all migration helpers |
| `cli/pages/tests/test_migration.py` | Unit tests for `MigrateFromV1Step` |

No existing files are renamed or restructured. `migration.py` is a new module in the existing `pipelines/` package, following the same pattern as `dev_engine.py`, `dev_scaffold.py`, `sync.py`, `cloud_crud.py`.

---

## 5. Changed Files

| File | Change |
|---|---|
| `cli/pages/pipelines/__init__.py` | Export `MigrateFromV1Step` |
| `cli/pages/executor.py` | Add `MigrateFromV1Step()` as first step in 7 executor functions |

---

## 6. Implementation Plan

### Step 1 — Core migration logic (`cli/pages/pipelines/migration.py`)

Implement `MigrateFromV1Step` as a `PipelineStep` subclass. Internal structure:

```
MigrateFromV1Step.execute(data)
  └─ _marker_path() → Path
  └─ _migration_log_path() → Path
  └─ _get_docker_client() → client | None
  └─ _find_old_page_containers(client) → list[ContainerInfo]
  └─ _migrate_page(client, container_info, argo_context) → None
       └─ _create_workspace(page_name, source_dir) → (workspace_key, workspace_path)
       └─ _restart_under_argo(source_dir, workspace_key, workspace_path, argo_context) → None
  └─ _stop_flask_manager(client) → None
  └─ _log_warning(page_name, reason) → None
  └─ _write_marker() → None
```

`ContainerInfo` is a small dataclass: `name`, `page_name`, `source_dir`, `status`.

`argo_context` is populated once (not per page): `(container, argo_adapter_port, argo_target_port)` — only resolved if at least one running page needs restarting.

### Step 2 — Export and inject

- Add `MigrateFromV1Step` to `cli/pages/pipelines/__init__.py`
- In `cli/pages/executor.py`, add `pipelines.MigrateFromV1Step()` as the first step in all 7 target functions

### Step 3 — Tests (`cli/pages/tests/test_migration.py`)

Write unit tests covering every case in the table in Section 3.4, plus:

- Marker present → Docker client never instantiated
- No old containers → marker written, no other calls made
- Mixed batch: 2 stopped pages + 1 running → workspaces created for all 3, restart called for 1 only
- Flask manager stopped only when no running old containers remain
- Flask manager not touched when running old containers still exist (edge case: running container migration failed mid-way)

Mock surface: `PageEngineClientManager`, `client.client.containers.list/get`, `argo_container_manager`, `register_page_in_argo`, `render_index_html`, `subprocess.Popen` (for copy_watcher and hot_reload_server).

---

## 7. Manual QA Addition

Add the following scenario to Section 12 of `docs/development/pages-argo-migration-status.md`:

**Step 13 — Upgrade path from old architecture**

Simulate an old-CLI user:
1. On the master branch, create a page with `dev add` and start it with `dev start`
2. Confirm the old container is running: `docker ps | grep page-`
3. Check out the migration branch, reinstall the CLI
4. Run `ubidots pages dev list` — expected: page appears as running or stopped, no error
5. Run `ubidots pages dev status` — expected: correct status
6. Run `ubidots pages dev logs` — expected: log output (not empty)
7. Confirm marker file exists: `cat ~/.ubidots_cli/.pages_v1_migration_done`
8. Confirm old container is gone: `docker ps -a | grep page-` should not show it
9. Confirm Argo route is registered: `curl -s http://localhost:8040/api/_/route/ | python3 -m json.tool`
10. Run `ubidots pages dev stop` — expected: exits 0

---

## 8. Open Questions (resolved)

| Question | Decision |
|---|---|
| Trigger: per-command or dedicated migrate command? | Per-command (first step, marker-gated) |
| Injection scope | All 7 `pages dev` commands that touch local dev state |
| Running pages during migration | Stop old container, restart under Argo silently |
| Failure granularity | Per-page — one page failing never aborts others |
| Marker written on partial success? | Yes — partial migration is permanently better than retry loops |
| Marker written on Docker-unavailable? | No — retries on next command |
| Output during migration | Silent unless warnings; one summary line pointing to log if warnings exist |
| Where to put migration code | New `cli/pages/pipelines/migration.py` module |
