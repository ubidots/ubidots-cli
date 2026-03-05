# Module Reference

Per-module breakdown of responsibilities, key files, data models, and API routes.

---

## Directory Map

| Directory | Responsibility |
|---|---|
| `cli/main.py` | Entry point; registers all sub-apps |
| `cli/settings.py` | Three-tier settings (Config / Functions / Pages) |
| `cli/compat.py` | Python version compatibility utilities |
| `cli/commons/` | Shared utilities used by all modules |
| `cli/config/` | Credential and profile management |
| `cli/devices/` | Device CRUD |
| `cli/variables/` | Variable CRUD |
| `cli/functions/` | Functions CRUD + local dev container engine |
| `cli/pages/` | Pages CRUD + local dev container engine |

---

## `commons/`

Shared code used by all modules. No module-specific logic lives here.

| File | Contents |
|---|---|
| `decorators.py` | Composable CLI option decorators (`@add_verbose_option`, `@simple_lookup_key`, etc.) |
| `enums.py` | Shared enums: `MessageColorEnum`, `TableColorEnum`, `EntityNameEnum`, `OutputFormatFieldsEnum` |
| `models.py` | Base Pydantic models with YAML/TOML serialization (`BaseYAMLDumpModel`, `BaseTOMLDumpModel`) |
| `pipelines.py` | `Pipeline` and `PipelineStep` base classes |
| `utils.py` | `build_endpoint()`, `get_instance_key()`, `check_response_status()`, `exit_with_error_message()`, `load_yaml()` |
| `validators.py` | `is_valid_object_id()`, `is_valid_json_string()` |

---

## `config/`

Profile creation, reading, and default management.

| File | Contents |
|---|---|
| `commands.py` | `ubidots config` command — interactive and non-interactive setup |
| `helpers.py` | `get_configuration()`, `get_profile_configuration()`, profile file I/O |
| `models.py` | `ProfileConfigModel` (Pydantic) — validates profile YAML structure |

Profiles are stored as YAML at `~/.ubidots_cli/profiles/<name>.yaml`. The active default is stored in `~/.ubidots_cli/config.yaml`.

---

## `devices/` and `variables/`

Simple CRUD modules. No executor or pipeline layer — commands call handlers directly.

```text
commands.py  →  handlers.py  →  Ubidots REST API
```

**API routes (devices):**

| Operation | Method | Route |
|---|---|---|
| list | GET | `/api/v2.0/devices/` |
| get | GET | `/api/v2.0/devices/{key}/` |
| add | POST | `/api/v2.0/devices/` |
| update | PATCH | `/api/v2.0/devices/{key}/` |
| delete | DELETE | `/api/v2.0/devices/{key}/` |

Variables follow the same pattern under `/api/v2.0/variables/`.

---

## `functions/`

Full pipeline architecture for both cloud CRUD and local container-based development.

```text
commands.py  →  executor.py  →  pipelines.py  →  handlers.py
                                     ↓
                               engines/docker/
```

**API routes:**

| Operation | Method | Route |
|---|---|---|
| list | GET | `/api/v2.0/functions/` |
| get | GET | `/api/v2.0/functions/{key}/` |
| add | POST | `/api/v2.0/functions/` |
| update | PATCH | `/api/v2.0/functions/{key}/` |
| delete | DELETE | `/api/v2.0/functions/{key}/` |
| push (upload) | PUT | `/api/v2.0/functions/{key}/code/` |
| pull (download) | GET | `/api/v2.0/functions/{key}/code/` |
| logs | GET | `/api/v2.0/functions/{key}/logs/` |

### Local Development Engine

The local dev environment runs two Docker containers connected on a shared bridge network.

#### Bridge Network

- **Name:** `ubidots_cli_function_rie`
- **Driver:** bridge
- All function containers and the Argo container join this network
- FRIE containers are **not** exposed to the host — all traffic enters through Argo
- Container hostnames inside the network equal their function labels, enabling internal DNS resolution

#### FRIE Container (Function Runtime Interface Environment)

The FRIE container runs the user's function code inside an AWS Lambda Runtime Interface Emulator (RIE).

| Property | Value |
|---|---|
| Image | `ubidots/functions-{runtime}` (e.g., `ubidots/functions-python3.11:base`) |
| Container label key | `ubidots_cli_function` |
| Internal port | `8080` (Lambda RIE invocation endpoint) |
| Invocation path | `/2015-03-31/functions/function/invocations` |
| Volume mount | Local project directory → `/var/task` (read-write) |
| Node.js extra mount | `node_modules` named volume → `/var/task/node_modules` (read-only) |
| Entrypoint command | `handler.main` (loads `handler.py` or `handler.js`, calls `main()`) |
| Environment variable | `AWS_LAMBDA_FUNCTION_TIMEOUT=<seconds>` |
| Host exposure | None — not exposed to host |

Each running function gets its own FRIE container. The container name and hostname are set to the function label, enabling Argo to reach it by name via internal Docker DNS.

#### Argo Container (API Adapter / Reverse Proxy)

Argo is a Ubidots-built reverse proxy that sits in front of all FRIE containers. A single Argo instance is shared across all running local functions.

| Property | Value |
|---|---|
| Image | `ubidots/functions-argo:2.0.1` |
| Container name | `argo` |
| Container label key | `ubidots_cli_argo` |
| Hostname inside network | `ubi.argo` |
| Adapter API port (host) | `127.0.0.1:8040` |
| Target port (host) | `127.0.0.1:8042` |

**Argo's responsibilities:**

- **CORS middleware** — injects `Access-Control-Allow-*` headers when enabled
- **HTTP method filtering** — rejects requests using methods not declared in the function config
- **Auth token validation** — enforces `X-Auth-Token` if configured
- **Request routing** — routes by URL path prefix (`/<function-label>/...`) to the correct FRIE container

**Configuring Argo via REST:**

After the FRIE container starts, the CLI POSTs an adapter configuration to Argo's REST API at `http://localhost:8040/api/v2/adapter`. A startup delay (`CONTAINER_STARTUP_DELAY_SECONDS` from settings, default `3` seconds) is applied first to give both containers time to initialize.

```python
# Adapter config posted to Argo
{
    "label": "<function-label>",
    "path": "<function-label>",
    "is_strict": True,
    "middlewares": [
        {"type": "allowed_methods", "methods": ["GET", "POST"]},
        {"type": "cors", "allow_origins": ["*"], ...}  # if cors=True
    ],
    "target": {
        "type": "rie_function",
        "url": "http://<function-label>:8080/2015-03-31/functions/function/invocations",
        "auth_token": "<token>"
    }
}
```

#### Request Flow

```text
Developer HTTP client
  → http://127.0.0.1:8040/<function-label>
      ↓ Argo: CORS middleware
      ↓ Argo: HTTP method check
      ↓ Argo: routes to FRIE via internal Docker DNS
          → http://<function-label>:8080/2015-03-31/functions/function/invocations
              ↓ Lambda RIE invokes handler()
              ← Response returned
      ← Argo forwards response
  ← Developer receives response
```

#### Container Lifecycle

| Operation | What happens |
|---|---|
| `dev start` | Ensure network exists → verify/pull image → start FRIE → start Argo (if not running) → POST adapter config to Argo |
| `dev stop` | Remove FRIE container → if no other FRIE containers remain, stop and remove Argo |
| `dev restart` | `container.restart()` on the FRIE container |
| `dev logs` | `container.logs(tail=N, follow=bool)` on the FRIE container |
| `dev status` | Query Docker for all containers labelled `ubidots_cli_function` |
| `dev clean` | Stop/remove all FRIE containers → stop/remove Argo → remove all `ubidots/functions-*` images → remove `ubidots_cli_function_rie` network |

**Argo auto-recovery:** On `dev start`, if Argo is found in `PAUSED` or `EXITED` state it is automatically restarted before proceeding.

---

## `pages/`

Full pipeline architecture mirroring the functions module structure.

```text
commands.py  →  executor.py  →  pipelines.py  →  handlers.py
                                     ↓
                               engines/docker/
```

**API routes:**

| Operation | Method | Route |
|---|---|---|
| list | GET | `/api/v2.0/pages/` |
| get | GET | `/api/v2.0/pages/{page_key}/` |
| add | POST | `/api/v2.0/pages/` |
| delete | DELETE | `/api/v2.0/pages/{page_key}/` |
| push (upload) | POST | `/api/v2.0/pages/{page_key}/code/` |
| pull (download) | GET | `/api/v2.0/pages/{page_key}/code/` |

### Local Page Dev Engine

Pages use a two-container stack: a Flask-based routing manager (`flask-pages-manager`, image `ubidots/pages-server:latest`, label key `ubidots_cli_pages_manager`, port `8044`) running on network `ubidots_cli_pages`, and per-page containers (label key `ubidots_cli_page`) that mount the page project directory and serve it with hot-reload support.

### Data Models

| Model | Description |
|---|---|
| `PageModel` | Remote page: `id, label, name` |
| `PageProjectModel` | Local project metadata: `name, label, createdAt, type` |
| `PageProjectMetadata` | Combined: both project and remote page info |
| `DashboardPageModel` | Concrete subclass of `BasePageModel`; validates required files: `manifest.toml`, `body.html`, `script.js`, `style.css` and `static/` directory |

Page projects include a `manifest.toml` (user-editable config) and a `.manifest.yaml` (auto-generated, stores linked remote ID and sync state).

---

## Configuration File Locations

| File | Purpose |
|---|---|
| `~/.ubidots_cli/config.yaml` | Active default profile name and global settings |
| `~/.ubidots_cli/profiles/<name>.yaml` | API domain, token, runtimes per profile |
| `~/.ubidots_cli/functions.ignore` | Glob patterns excluded from push/pull |
| `<project>/.manifest.yaml` | Auto-generated: remote ID, timestamps, sync state |
| `<project>/manifest.toml` | User-editable: name, runtime, methods, CORS, etc. |
