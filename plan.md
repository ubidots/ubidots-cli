# `pages dev migrate` Command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `ubidots pages dev migrate` command that discovers and removes legacy Docker containers from the old dual-container architecture (Flask manager + per-page containers), printing the recovered source paths so the user knows where to run `dev start`.

**Architecture:** A single new pipeline step `MigrateLegacyContainersStep` is added to `cli/pages/pipelines/dev_engine.py`. It uses the Docker SDK (already available via `data["client"]`) to find old containers by label and by name, reads their volume mounts to recover source paths, confirms with the user, then stops and removes them. The executor and command wiring follow the exact same patterns as `clean_orphaned_pages`.

**Tech Stack:** Python, Docker SDK (`docker` package), Typer, existing `PipelineStep` / `Pipeline` infrastructure.

---

## File Map

| File | Change |
|------|--------|
| `cli/pages/pipelines/dev_engine.py` | Add `MigrateLegacyContainersStep` class |
| `cli/pages/executor.py` | Add `migrate_legacy_pages()` function |
| `cli/pages/commands.py` | Add `migrate` command under `dev_app` |
| `cli/pages/tests/test_dev_engine_steps.py` | Add tests for `MigrateLegacyContainersStep` |
| `cli/pages/tests/test_dev_commands.py` | Add tests for the `migrate` CLI command |

---

### Task 1: `MigrateLegacyContainersStep` — failing tests first

**Files:**
- Modify: `cli/pages/tests/test_dev_engine_steps.py`

- [ ] **Step 1: Add the failing tests**

Append to `cli/pages/tests/test_dev_engine_steps.py`:

```python
from unittest.mock import MagicMock, call, patch

from cli.pages.pipelines.dev_engine import MigrateLegacyContainersStep


# ── MigrateLegacyContainersStep ────────────────────────────────────────────────

def _make_page_container(name: str, source_path: str) -> MagicMock:
    """Build a mock legacy page container with correct volume mount structure."""
    container = MagicMock()
    container.name = name
    container.attrs = {
        "Mounts": [
            {"Destination": "/app/page", "Source": source_path, "Type": "bind"},
        ]
    }
    return container


def test_migrate_no_legacy_containers_prints_message(capsys):
    client = MagicMock()
    client.client.containers.list.return_value = []
    client.client.containers.get.side_effect = Exception("not found")

    data = {"client": client, "confirm": True}
    MigrateLegacyContainersStep().execute(data)

    captured = capsys.readouterr()
    assert "No legacy" in captured.out


def test_migrate_stops_and_removes_page_containers():
    c1 = _make_page_container("page-my_page", "/home/user/my_page")
    c2 = _make_page_container("page-dashboard1", "/home/user/dashboard1")
    client = MagicMock()
    client.client.containers.list.return_value = [c1, c2]
    client.client.containers.get.side_effect = Exception("not found")  # no flask manager

    data = {"client": client, "confirm": True}
    MigrateLegacyContainersStep().execute(data)

    c1.stop.assert_called_once()
    c1.remove.assert_called_once()
    c2.stop.assert_called_once()
    c2.remove.assert_called_once()


def test_migrate_stops_flask_manager_when_present():
    flask = MagicMock()
    flask.name = "flask-pages-manager"
    client = MagicMock()
    client.client.containers.list.return_value = []
    client.client.containers.get.return_value = flask

    data = {"client": client, "confirm": True}
    MigrateLegacyContainersStep().execute(data)

    flask.stop.assert_called_once()
    flask.remove.assert_called_once()


def test_migrate_recovers_source_paths():
    c1 = _make_page_container("page-my_page", "/home/user/my_page")
    c2 = _make_page_container("page-dashboard1", "/home/user/dashboard1")
    client = MagicMock()
    client.client.containers.list.return_value = [c1, c2]
    client.client.containers.get.side_effect = Exception("not found")

    data = {"client": client, "confirm": True}
    result = MigrateLegacyContainersStep().execute(data)

    assert result["migrated_paths"] == ["/home/user/my_page", "/home/user/dashboard1"]


def test_migrate_sets_empty_paths_when_no_page_containers():
    flask = MagicMock()
    client = MagicMock()
    client.client.containers.list.return_value = []
    client.client.containers.get.return_value = flask

    data = {"client": client, "confirm": True}
    result = MigrateLegacyContainersStep().execute(data)

    assert result["migrated_paths"] == []


def test_migrate_queries_correct_label():
    client = MagicMock()
    client.client.containers.list.return_value = []
    client.client.containers.get.side_effect = Exception()

    MigrateLegacyContainersStep().execute({"client": client, "confirm": True})

    client.client.containers.list.assert_called_once_with(
        all=True, filters={"label": "ubidots_cli_page=true"}
    )


def test_migrate_queries_correct_flask_manager_name():
    client = MagicMock()
    client.client.containers.list.return_value = []
    client.client.containers.get.side_effect = Exception()

    MigrateLegacyContainersStep().execute({"client": client, "confirm": True})

    client.client.containers.get.assert_called_once_with("flask-pages-manager")


def test_migrate_tolerates_stop_failure():
    """A container.stop() failure must not abort the migration."""
    c1 = _make_page_container("page-my_page", "/home/user/my_page")
    c1.stop.side_effect = Exception("already stopped")
    client = MagicMock()
    client.client.containers.list.return_value = [c1]
    client.client.containers.get.side_effect = Exception()

    data = {"client": client, "confirm": True}
    MigrateLegacyContainersStep().execute(data)  # must not raise

    c1.remove.assert_called_once()
```

- [ ] **Step 2: Run tests to confirm they all fail**

```bash
cd /home/inumaki/Desktop/temp-cli/ubidots-cli
pytest cli/pages/tests/test_dev_engine_steps.py -k "migrate" -v
```

Expected: all 8 tests `ERROR` or `FAIL` with `ImportError: cannot import name 'MigrateLegacyContainersStep'`.

---

### Task 2: Implement `MigrateLegacyContainersStep`

**Files:**
- Modify: `cli/pages/pipelines/dev_engine.py`

- [ ] **Step 1: Add the class**

Append to the bottom of `cli/pages/pipelines/dev_engine.py` (before the last existing class, or at the very end):

```python
class MigrateLegacyContainersStep(PipelineStep):
    """Stop and remove containers left over from the old Flask+Docker architecture."""

    _LEGACY_PAGE_LABEL = "ubidots_cli_page=true"
    _LEGACY_FLASK_MANAGER_NAME = "flask-pages-manager"
    _LEGACY_PAGE_MOUNT_DEST = "/app/page"

    def execute(self, data):
        client = data["client"]
        confirm = data.get("confirm", False)

        # Discover old page containers (label ubidots_cli_page=true)
        try:
            page_containers = client.client.containers.list(
                all=True,
                filters={"label": self._LEGACY_PAGE_LABEL},
            )
        except Exception:
            page_containers = []

        # Discover flask manager container
        flask_container = None
        try:
            flask_container = client.client.containers.get(
                self._LEGACY_FLASK_MANAGER_NAME
            )
        except Exception:
            pass

        if not page_containers and flask_container is None:
            typer.echo("No legacy page containers found. Nothing to migrate.")
            data["migrated_paths"] = []
            return data

        # Recover source paths from volume mounts
        source_paths: list[str] = []
        for container in page_containers:
            for mount in container.attrs.get("Mounts", []):
                if mount.get("Destination") == self._LEGACY_PAGE_MOUNT_DEST:
                    source_paths.append(mount.get("Source", "(unknown)"))
                    break

        # Print summary
        names = [c.name for c in page_containers]
        if flask_container:
            names.append(self._LEGACY_FLASK_MANAGER_NAME)
        typer.echo(f"Found {len(names)} legacy container(s):")
        for name in names:
            typer.echo(f"  {name}")
        typer.echo("")

        if not confirm and not typer.confirm("Remove all legacy containers?"):
            raise typer.Abort()

        # Stop and remove — best-effort per container
        for container in page_containers:
            with suppress(Exception):
                container.stop()
            with suppress(Exception):
                container.remove()

        if flask_container:
            with suppress(Exception):
                flask_container.stop()
            with suppress(Exception):
                flask_container.remove()

        typer.echo(f"Removed {len(names)} legacy container(s).")

        if source_paths:
            typer.echo(
                "\nRun 'ubidots pages dev start' inside each directory to resume "
                "with the new backend:"
            )
            for path in source_paths:
                typer.echo(f"  {path}")

        data["migrated_paths"] = source_paths
        return data
```

- [ ] **Step 2: Run the tests to confirm they pass**

```bash
pytest cli/pages/tests/test_dev_engine_steps.py -k "migrate" -v
```

Expected: all 8 tests `PASSED`.

- [ ] **Step 3: Run the full step test suite to check for regressions**

```bash
pytest cli/pages/tests/test_dev_engine_steps.py -v
```

Expected: all tests `PASSED`.

- [ ] **Step 4: Commit**

```bash
git add cli/pages/pipelines/dev_engine.py cli/pages/tests/test_dev_engine_steps.py
git commit -m "feat: add MigrateLegacyContainersStep for old Docker architecture cleanup"
```

---

### Task 3: Executor function

**Files:**
- Modify: `cli/pages/executor.py`

- [ ] **Step 1: Add the failing test**

Append to `cli/pages/tests/test_dev_commands.py`:

```python
class TestMigrateCommand(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    @patch("cli.pages.commands.executor.migrate_legacy_pages")
    def test_migrate_command_default(self, mock_migrate):
        result = self.runner.invoke(app, ["dev", "migrate"])
        self.assertEqual(result.exit_code, 0)
        mock_migrate.assert_called_once_with(confirm=False, verbose=False)

    @patch("cli.pages.commands.executor.migrate_legacy_pages")
    def test_migrate_command_with_yes_flag(self, mock_migrate):
        result = self.runner.invoke(app, ["dev", "migrate", "--yes"])
        self.assertEqual(result.exit_code, 0)
        mock_migrate.assert_called_once_with(confirm=True, verbose=False)

    @patch("cli.pages.commands.executor.migrate_legacy_pages")
    def test_migrate_command_with_verbose(self, mock_migrate):
        result = self.runner.invoke(app, ["dev", "migrate", "--verbose"])
        self.assertEqual(result.exit_code, 0)
        mock_migrate.assert_called_once_with(confirm=False, verbose=True)

    def test_migrate_command_help(self):
        result = self.runner.invoke(app, ["dev", "migrate", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("legacy", result.stdout.lower())
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest cli/pages/tests/test_dev_commands.py -k "migrate" -v
```

Expected: `FAIL` — `AttributeError: module 'cli.pages.executor' has no attribute 'migrate_legacy_pages'` (or `ImportError` on the command).

- [ ] **Step 3: Add the executor function**

Append to `cli/pages/executor.py`:

```python
def migrate_legacy_pages(confirm: bool, verbose: bool):
    steps = [
        pipelines.GetClientStep(),
        pipelines.MigrateLegacyContainersStep(),
    ]
    pipeline = Pipeline(steps, success_message="")
    pipeline.run(
        {
            "confirm": confirm,
            "verbose": verbose,
            "root": migrate_legacy_pages.__name__,
        }
    )
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest cli/pages/tests/test_dev_commands.py -k "migrate" -v
```

Expected: `FAIL` — still failing because the command is not wired in `commands.py` yet. The executor mock tests should `PASS`; the help test will fail until Task 4.

> Note: only the 3 mock tests pass here — the help test stays failing until the command exists. That is expected.

- [ ] **Step 5: Commit the executor only**

```bash
git add cli/pages/executor.py cli/pages/tests/test_dev_commands.py
git commit -m "feat: add migrate_legacy_pages executor function"
```

---

### Task 4: Wire the `migrate` command

**Files:**
- Modify: `cli/pages/commands.py`

- [ ] **Step 1: Add the help text constant and command**

In `cli/pages/commands.py`, add the constant near the other help text strings (after `CLEAN_COMMAND_HELP_TEXT`):

```python
MIGRATE_COMMAND_HELP_TEXT = (
    "Stop and remove legacy page containers from the old Docker-based architecture. "
    "Prints the source directories of discovered pages so you can restart them "
    "with 'dev start'."
)
```

Then add the command function after the `clean_pages` command (before the `logs_page` command):

```python
@dev_app.command(name="migrate", help=MIGRATE_COMMAND_HELP_TEXT)
@add_verbose_option()
def migrate_pages(
    confirm: Annotated[
        bool,
        typer.Option(
            "--yes", "-y", help="Skip confirmation prompt and remove immediately."
        ),
    ] = False,
    verbose: bool = False,
):
    executor.migrate_legacy_pages(confirm=confirm, verbose=verbose)
```

- [ ] **Step 2: Run all migrate tests**

```bash
pytest cli/pages/tests/test_dev_commands.py -k "migrate" -v
```

Expected: all 4 tests `PASSED`.

- [ ] **Step 3: Run the full command test suite**

```bash
pytest cli/pages/tests/test_dev_commands.py -v
```

Expected: all tests `PASSED`.

- [ ] **Step 4: Smoke-test the help output manually**

```bash
python -m cli.main pages dev migrate --help
```

Expected output includes `--yes`, `--verbose`, and a description mentioning legacy containers.

- [ ] **Step 5: Commit**

```bash
git add cli/pages/commands.py
git commit -m "feat: add 'pages dev migrate' command to clean up legacy Docker containers"
```

---

### Task 5: Run the full pages test suite

- [ ] **Step 1: Run all pages tests**

```bash
pytest cli/pages/tests/ -v
```

Expected: all tests `PASSED`, zero failures.

- [ ] **Step 2: Run the functions tests to check for regressions (shared Docker/Argo code)**

```bash
pytest cli/functions/tests/ -v
```

Expected: all tests `PASSED`.

- [ ] **Step 3: Final commit if any fixups were needed**

If any test needed adjustment to fix an import or typo:

```bash
git add -p
git commit -m "fix: address test issues found in full suite run"
```

---

## Self-Review

**Spec coverage:**
- ✅ Finds old page containers by label `ubidots_cli_page=true`
- ✅ Finds `flask-pages-manager` by name
- ✅ Reads `/app/page` mount to recover source paths
- ✅ Confirmation prompt (skippable with `--yes`)
- ✅ Best-effort stop/remove (individual failures don't abort migration)
- ✅ Prints source paths for restart instructions
- ✅ No old architecture code imported or preserved

**Placeholder scan:** None found — all code blocks are complete.

**Type consistency:**
- `MigrateLegacyContainersStep` referenced in executor as `pipelines.MigrateLegacyContainersStep()` — matches class name in dev_engine.py ✅
- `migrate_legacy_pages` referenced in commands as `executor.migrate_legacy_pages` — matches function name in executor.py ✅
- `data["migrated_paths"]` set by the step — not consumed by any downstream step (no coupling needed) ✅
- `data["client"]` provided by `GetClientStep` (existing) — consumed by `MigrateLegacyContainersStep` via `client.client.containers` (same pattern as `TryGetArgoPortStep`) ✅
