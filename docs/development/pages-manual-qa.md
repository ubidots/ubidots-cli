# Pages Dev — Manual QA Walkthrough

**Branch:** `back/SC-2277__pages-argo-pr2`

**Before starting:**
- Docker is running
- `ubidots/functions-argo:2.1.0` image available: `docker images | grep argo`
- CLI installed from this branch
- A valid profile configured
- Working directory is a temporary scratch folder (not inside any existing page)

Throughout: `{key}` = workspace key printed in `dev start` output (e.g. `smoke-ab12cd34`).

---

## A — `dev add`

### A1 — Default name
```bash
ubidots pages dev add
```
Expected: exits 0. Directory `my_page/` created with `body.html`, `manifest.toml`,
`script.js`, `style.css`, `static/`. Workspace at `~/.ubidots_cli/pages/my_page-XXXXXXXX/`
also created.

### A2 — Custom name
```bash
ubidots pages dev add --name smoke-qa
```
Expected: exits 0. Directory `smoke-qa/` created. Workspace at
`~/.ubidots_cli/pages/smoke-qa-XXXXXXXX/` created.

### A3 — Verbose flag (both forms)
```bash
ubidots pages dev add --name smoke-verbose -v
ubidots pages dev add --name smoke-verbose2 --verbose
```
Expected: both exit 0, pipeline step output visible.

### A4 — Fails inside an existing page directory
```bash
cd smoke-qa
ubidots pages dev add --name inner
cd ..
```
Expected: exits non-zero. Error says cannot run `dev add` from inside a page directory.

### A5 — Fails if directory already exists
```bash
ubidots pages dev add --name smoke-qa
```
Expected: exits non-zero. Error says page already exists.

---

## B — Full lifecycle (happy path)

All steps in this section run from inside `smoke-qa/`:
```bash
cd smoke-qa
```

### B1 — Start
```bash
ubidots pages dev start
```
Expected: exits 0. Output includes URL `http://localhost:8042/{key}/`. Note the key.

### B2 — Argo route registered with correct payload
```bash
curl -s http://localhost:8040/api/_/route/ | python3 -m json.tool
```
Expected: response contains entry with `"label": "pages-{key}"`,
`"bridge": { "target": { "type": "local_file", "base_path": "/pages/{key}" } }`.

### B3 — Page loads in browser
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8042/{key}/
```
Expected: `200`.

### B4 — Static asset loads
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8042/{key}/script.js
```
Expected: `200`.

### B5 — Hot reload fires on file change
Edit `body.html` in the source directory (add any character and save). Within 2 seconds
a browser tab open at the page URL should reload automatically.

### B6 — Stop
```bash
ubidots pages dev stop
```
Expected: exits 0.

### B7 — Argo route deregistered
```bash
curl -s http://localhost:8040/api/_/route/ | python3 -m json.tool
```
Expected: `pages-{key}` no longer present in the array.

---

## C — `dev status`

### C1 — Status while running
```bash
ubidots pages dev start
ubidots pages dev status
```
Expected: exits 0. Output shows page name, `running`, and the URL.

### C2 — Verbose (both forms)
```bash
ubidots pages dev status -v
ubidots pages dev status --verbose
```
Expected: both exit 0. Pipeline step output visible. Same status table.

### C3 — Status while stopped
```bash
ubidots pages dev stop
ubidots pages dev status
```
Expected: exits 0. Output shows `stopped`, no URL.

### C4 — Fails outside a page directory
```bash
cd /tmp
ubidots pages dev status
cd -
```
Expected: exits non-zero. Error says not in a page directory.

---

## D — `dev list`

### D1 — List while running
```bash
cd smoke-qa && ubidots pages dev start
cd ..
ubidots pages dev list
```
Expected: exits 0. Row shows page name, `running`, URL, source path.

### D2 — Verbose (both forms)
```bash
ubidots pages dev list -v
ubidots pages dev list --verbose
```
Expected: both exit 0. Pipeline step output visible.

### D3 — List while stopped
```bash
cd smoke-qa && ubidots pages dev stop && cd ..
ubidots pages dev list
```
Expected: exits 0. Row shows page name, `stopped`, no URL.

### D4 — List with multiple pages
```bash
ubidots pages dev add --name smoke-b
cd smoke-qa && ubidots pages dev start && cd ..
cd smoke-b && ubidots pages dev start && cd ..
ubidots pages dev list
```
Expected: both pages visible, both `running` with their respective URLs.
```bash
cd smoke-qa && ubidots pages dev stop && cd ..
cd smoke-b && ubidots pages dev stop && cd ..
```

---

## E — `dev logs`

From inside `smoke-qa/` with the page running:
```bash
cd smoke-qa && ubidots pages dev start
```

### E1 — All logs
```bash
ubidots pages dev logs
```
Expected: exits 0. Output contains lines from hot-reload server and copy-watcher.

### E2 — Tail (both flag forms)
```bash
ubidots pages dev logs --tail 5
ubidots pages dev logs -n 5
```
Expected: both exit 0. At most 5 lines of output each.

### E3 — Follow (both flag forms)
```bash
timeout 3 ubidots pages dev logs --follow; echo "exit: $?"
timeout 3 ubidots pages dev logs -f; echo "exit: $?"
```
Expected: both stream output for 3 seconds then terminate. Exit code `0` or `124`.
No error before the timeout.

### E4 — Verbose (both forms)
```bash
ubidots pages dev logs -v
ubidots pages dev logs --verbose
```
Expected: both exit 0. Pipeline step output visible.

### E5 — Fails outside a page directory
```bash
cd /tmp
ubidots pages dev logs
cd -
```
Expected: exits non-zero. Error says not in a page directory.

```bash
cd smoke-qa && ubidots pages dev stop && cd ..
```

---

## F — `dev restart`

### F1 — Restart while running
```bash
cd smoke-qa && ubidots pages dev start
ubidots pages dev restart
```
Expected: exits 0. Page briefly stops then comes back up.

### F2 — Argo route re-registered after restart
```bash
curl -s http://localhost:8040/api/_/route/ | python3 -m json.tool
```
Expected: `pages-{key}` present with `local_file` target.

### F3 — Verbose (both forms)
```bash
ubidots pages dev restart -v
ubidots pages dev restart --verbose
```
Expected: both exit 0. Pipeline step output visible.

### F4 — Fails when not running
```bash
ubidots pages dev stop
ubidots pages dev restart
```
Expected: exits non-zero. Error says page is not running.

### F5 — Fails outside a page directory
```bash
cd /tmp
ubidots pages dev restart
cd -
```
Expected: exits non-zero. Error says not in a page directory.

```bash
cd smoke-qa && ubidots pages dev start && cd ..
```

---

## G — Guard conditions

### G1 — `dev start` when already running
```bash
cd smoke-qa
ubidots pages dev start
ubidots pages dev start
```
Expected: second invocation exits non-zero. Error says page already running with URL.

### G2 — `dev stop` when not running
```bash
ubidots pages dev stop
ubidots pages dev stop
```
Expected: second invocation exits non-zero. Error says page is not running.

### G3 — `dev stop` outside page directory
```bash
cd /tmp
ubidots pages dev stop
cd -
```
Expected: exits non-zero (reads `.manifest.yaml` which doesn't exist).

### G4 — `dev start` outside page directory
```bash
cd /tmp
ubidots pages dev start
cd -
```
Expected: exits non-zero. Error says not in a page directory.

### G5 — `dev restart` outside page directory
```bash
cd /tmp
ubidots pages dev restart
cd -
```
Expected: exits non-zero. Error says not in a page directory.

---

## H — Crash recovery (stale Argo route)

```bash
cd smoke-qa && ubidots pages dev start
```

Kill the page processes without `dev stop`:
```bash
kill $(cat .pid) $(cat .watcher.pid)
rm -f .pid .watcher.pid
```

Confirm the stale Argo route is still registered:
```bash
curl -s http://localhost:8040/api/_/route/ | python3 -m json.tool
```
Expected: `pages-{key}` still present.

Start again — must succeed despite stale route:
```bash
ubidots pages dev start
```
Expected: exits 0. `DeregisterPageFromArgoStep` removes stale route, fresh one registered.

```bash
curl -s http://localhost:8040/api/_/route/ | python3 -m json.tool
```
Expected: `pages-{key}` present again.

```bash
ubidots pages dev stop
```

---

## I — `dev clean`

Set up an orphaned workspace (source directory does not exist):
```bash
mkdir -p ~/.ubidots_cli/pages/orphan-qa-deadbeef
echo "/nonexistent/path/that/does/not/exist" > ~/.ubidots_cli/pages/orphan-qa-deadbeef/.source_path
```

### I1 — Interactive prompt (no flags)
```bash
cd /tmp
ubidots pages dev clean
```
Expected: exits 0. Lists orphaned page. Prompts "Remove all orphaned pages?".
Answer `y` — orphan workspace is deleted.

### I2 — Skip prompt with --yes
```bash
mkdir -p ~/.ubidots_cli/pages/orphan-qa-deadbeef
echo "/nonexistent/path" > ~/.ubidots_cli/pages/orphan-qa-deadbeef/.source_path
ubidots pages dev clean --yes
```
Expected: exits 0. Orphan silently removed. No prompt shown.

### I3 — Skip prompt with -y (short form)
```bash
mkdir -p ~/.ubidots_cli/pages/orphan-qa-deadbeef
echo "/nonexistent/path" > ~/.ubidots_cli/pages/orphan-qa-deadbeef/.source_path
ubidots pages dev clean -y
```
Expected: same as I2.

### I4 — No orphans found
```bash
ubidots pages dev clean
```
Expected: exits 0. Output says `"No orphaned pages found."`.

### I5 — Verbose (both forms)
```bash
ubidots pages dev clean -v
ubidots pages dev clean --verbose
```
Expected: both exit 0. Pipeline step output visible.

---

## J — Functions + Pages sharing Argo

Navigate to a valid function project directory:
```bash
cd /path/to/your-function
ubidots functions dev start
```
Expected: exits 0. Argo container starts (or reuses). Function route registered.

```bash
curl -s http://localhost:8040/api/_/route/ | python3 -m json.tool
```
Expected: entry with `"bridge": { "target": { "type": "http" } }` for the function.

Now start a page in a different terminal tab:
```bash
cd /path/to/smoke-qa
ubidots pages dev start
```
Expected: exits 0. Argo container reused (not restarted). Page route added alongside
function route.

```bash
curl -s http://localhost:8040/api/_/route/ | python3 -m json.tool
```
Expected: both routes present simultaneously.

Stop the page — function must keep working:
```bash
ubidots pages dev stop
curl -s http://localhost:8040/api/_/route/ | python3 -m json.tool
```
Expected: only function route remains. Argo container still running.

```bash
ubidots functions dev stop
```

### J1 — Functions dev start verbose (both forms)
```bash
ubidots functions dev start -v
ubidots functions dev stop
ubidots functions dev start --verbose
ubidots functions dev stop
```
Expected: both exit 0. Pipeline steps visible including Argo registration step.

---

## K — Cleanup

```bash
cd smoke-qa && ubidots pages dev stop 2>/dev/null; cd ..
ubidots pages dev clean -y
docker ps | grep argo
```
Expected: Argo container may still be running (it stays up). Remove it manually if needed:
```bash
docker rm -f argo
```
