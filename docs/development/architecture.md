# Architecture

This document describes the structural patterns, design decisions, and wiring used throughout the Ubidots CLI codebase.
Read this before making changes to understand how the pieces fit together.

---

## Overview

The Ubidots CLI is a Python command-line application built on [Typer](https://typer.tiangolo.com/)
(which wraps [Click](https://click.palletsprojects.com/)). It communicates with the Ubidots REST API via
[httpx](https://www.python-httpx.org/), validates data with [Pydantic v2](https://docs.pydantic.dev/),
and formats terminal output using [Rich](https://github.com/Textualize/rich).

**Package entry point:** `cli/main.py` → `ubidots` CLI command

The top-level app registers five sub-apps:

```python
app = typer.Typer()
app.command(help="Configure general settings for the CLI.")(config)
app.add_typer(function_app, name="functions")
app.add_typer(device_app, name="devices")
app.add_typer(variable_app, name="variables")
app.add_typer(page_app, name="pages")
```

---

## Pipeline Pattern

All non-trivial operations execute as a **Pipeline** — an ordered list of `PipelineStep` objects that pass a shared
data dictionary through each step sequentially.

```python
# cli/commons/pipelines.py

@dataclass
class Pipeline:
    steps: list[PipelineStep]
    success_message: str = ""

    def run(self, initial_data: dict) -> dict:
        data = initial_data
        for step in self.steps:
            try:
                data = step.perform_step(data)
            except Exception as error:
                self._handle_failure(step, error)
                break
        else:
            self._handle_success()
        return data
```

### How steps work

Each step implements `perform_step(data: dict) -> dict`. It reads what it needs from `data`, performs one focused
operation, writes its results back into `data`, and returns it.

```text
Pipeline.run({"profile": "default", "page_key": "abc"})
  → GetActiveConfigStep       adds data["active_config"]
  → FetchRemotePageStep       adds data["page"]
  → FormatOutputStep          renders table/json
  → (all succeeded)           prints success message and exits 0
  → (any exception raised)    prints styled error panel and exits 1
```

### Error handling

When any step raises an exception, `_handle_failure()` calls `exit_with_error_message()` from `cli/commons/utils.py`.
This prints a Rich-formatted error panel and exits with code `1`. Steps should raise specific named exceptions
(e.g., `PageAlreadyExistsInCurrentDirectoryError`) rather than generic ones so the error message is actionable.

### Verbose mode

When `--verbose` is passed, each pipeline step emits a status log (`"(Starting OK)"`, `"(Finished OK)"`,
`"(Finished ERROR)"`) as it executes, making it possible to see exactly where a pipeline fails.

---

## Command → Executor → Pipeline → Handler

Complex modules (functions, pages) use a four-layer call chain:

```text
commands.py       CLI layer      Typer options, arguments, type annotations
    ↓
executor.py       Orchestrator   Builds and runs the correct pipeline
    ↓
pipelines.py      Steps          One focused operation per step class
    ↓
handlers.py       HTTP layer     Raw httpx calls to the Ubidots API
```

Simpler modules (devices, variables) skip the executor and pipeline layers and call handlers directly from commands.

### Why this separation?

- **Commands** stay thin — they parse CLI input and delegate immediately.
- **Executors** own the "which steps does this operation need?" logic, decoupled from the CLI surface.
- **Steps** are independently testable and reusable across different executors.
- **Handlers** are pure HTTP — no business logic, easy to mock in tests.

---

## Decorator Pattern for Shared CLI Options

`cli/commons/decorators.py` provides composable decorators that dynamically inject annotated parameters into command
functions, eliminating repetition across dozens of commands.

```python
@app.command()
@add_verbose_option()
@add_pagination_options()
@simple_lookup_key(entity_name=EntityNameEnum.DEVICE)
def get_device(id, label, page, page_size, verbose):
    ...
```

| Decorator | Options injected |
|---|---|
| `@add_verbose_option()` | `--verbose` / `-v` (single flag) |
| `@add_pagination_options()` | `--page INTEGER`, `--page-size INTEGER` |
| `@add_sort_by_option()` | `--sort-by TEXT` |
| `@add_filter_option()` | `--filter TEXT` |
| `@simple_lookup_key(entity)` | `--id TEXT`, `--label TEXT` with ID precedence |

Each decorator uses `functools.wraps` and `typing.Annotated` to attach `typer.Option` metadata so Typer generates
the correct help text, types, and defaults automatically.

---

## Profile-Based Authentication

Every remote command accepts `--profile` to select a named credential set. If omitted, the default profile from
`~/.ubidots_cli/config.yaml` is used.

Profiles are stored as YAML files at `~/.ubidots_cli/profiles/<name>.yaml` and validated by `ProfileConfigModel` in `cli/config/models.py`.

The helper `get_configuration(profile: str)` in `cli/config/helpers.py` resolves which profile to load. It is called
in a `GetActiveConfigStep` near the start of every pipeline that needs API access.

---

## Container Engine Abstraction

Both `functions` and `pages` modules support Docker via independent engine implementations. Functions additionally
supports Podman. The engine is selected from `settings.CONFIG.DEFAULT_CONTAINER_ENGINE`.

**Functions engine** (`cli/functions/engines/`):

```text
cli/functions/engines/
├── abstracts/
│   └── client.py       AbstractEngineClient protocol
├── docker/
│   ├── container.py    Container lifecycle (start, stop, restart, logs, status)
│   ├── image.py        Image pull and verification
│   ├── network.py      Bridge network management
│   ├── models.py       Container status data models
│   └── validators.py   Pre-start validation
├── podman/             Mirrors Docker implementation
├── models.py           Shared engine models
├── manager.py          Engine client factory
└── settings.py         Engine-specific settings
```

**Pages engine** (`cli/pages/engines/`):

```text
cli/pages/engines/
├── docker/
│   ├── client.py       Concrete Docker client
│   ├── container.py    Container lifecycle
│   ├── network.py      Network management
│   ├── models.py       Container status models
│   └── helpers.py      Engine helper utilities
└── manager.py          Engine client factory
```

Pages has no Podman implementation. The rest of the codebase (executors, pipelines) calls the abstract interface
and never imports Docker or Podman directly, keeping container engine concerns fully isolated.
