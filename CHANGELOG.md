# Changelog

## [Unreleased]

## [1.0.0] - 2026-03-18

### 🔄 Breaking Changes

#### **Functions**

- **Runtime strings are now API-driven**: The `--runtime` option in `ubidots functions dev add`
  no longer accepts a fixed enum. It now accepts any runtime identifier returned by your
  account's API (e.g. `python3.12`, `nodejs20.x`). Previously only a fixed set of values were
  accepted.
- **Local dev commands moved under `functions dev`**: Commands for local UbiFunction development
  are now organized under the `ubidots functions dev` subgroup (e.g. `ubidots functions dev
  start`, `ubidots functions dev logs`). The legacy top-level aliases (`ubidots functions start`,
  `ubidots functions init`) are deprecated.
- **Remote logs command restructured**: `ubidots functions logs` is now a dedicated remote-only
  command that accepts an optional function ID argument and `--tail`/`-n`. The previous
  `--remote` flag approach is replaced by this top-level command.

### ✨ New Features

#### **Pages Module (new)**

- Added full `ubidots pages` command group for managing Ubidots custom dashboard pages
- Remote CRUD: `add`, `get`, `update`, `delete`, `list`, `push`, `pull`
- Added `ubidots pages update` command — rename a remote page by `--id` or `--label` using `--new-name`
- Added local development environment via `ubidots pages dev` subgroup: `add`, `start`, `stop`,
  `restart`, `status`, `list`, `logs`
- Added `ubidots pages dev logs` command — stream or tail local page server container logs with
  `--follow`/`-f` and `--tail N`/`-n N`
- Page names with spaces are fully supported — sanitized to hyphens in container names and URLs

#### **Functions**

- Added `--tail N` / `-n N` option to `ubidots functions logs` (remote) to limit the number of log entries shown
- Exposed `--timeout` option in `ubidots functions dev add` — previously functional but hidden from `--help`
- Added `ubidots functions dev clean` command to clean up the local dev environment
- Added `--help` section grouping: commands are now organized into **Cloud Commands** and **Sync Commands** panels
- Runtime validation error in `ubidots functions dev add` now lists all runtimes available for the configured profile
- Added support for modern Python runtimes (e.g. `python3.12`, `python3.13`) via API-driven
  runtime strings — no CLI upgrade required when Ubidots adds new runtimes

#### **Python Support**

- Added Python 3.13 and 3.14 support (version constraint expanded from `<3.13` to `<3.15`)
- Upgraded `typer` from `^0.12.0` to `^0.15.0` for compatibility with click 8.3.x on newer Python versions
- Added `py313` to tox test matrix

### 🐛 Bug Fixes

#### **Functions**

- Fixed `functions dev start` failing on macOS — internal Docker container IP replaced with `127.0.0.1` for host accessibility
- Fixed `permission denied` error when stopping a Node.js function on macOS — `node_modules`
  (created as root inside the container) is now removed via Docker exec instead of the host
  filesystem
- Improved error message when running `functions` commands outside a function directory

#### **Pages**

- Fixed `pages dev start` failing with "Invalid container name" for page names containing spaces
- Fixed page URL and `PAGE_NAME` environment variable inside the container when the page name contains spaces
- Fixed `pages push` crashing for locally-created pages that have no remote ID yet
- Fixed `pages dev logs --follow` timing out after 60 seconds — log output now streams correctly
- Fixed `flask-pages-manager` container failing to start due to permission errors — container
  now starts as root with dependencies pre-installed
- Improved error message when running `pages` commands outside a page directory

### 🔒 Security

- Removed excessive Docker privileges from the pages engine `Dockerfile`

## [0.2.0] - 2025-01-27

### 🔄 Breaking Changes

#### **Functions Commands**

- **REMOVED**: `ubidots functions new`
- **REPLACED WITH**: `ubidots functions init`
  ```bash
  # OLD (no longer works)
  ubidots functions new my-function --language python

  # NEW
  ubidots functions init my-function --language python
  ```

- **NEW CAPABILITY**: `init` can now pull from remote
  ```bash
  # Pull existing function from remote
  ubidots functions init --remote-id 67ef05f2c9917a07b8f04519
  ```

#### **Configuration Changes**

- **CHANGED**: Profile storage location moved from single config file to individual profile files
- **OLD**: `~/.ubidots_cli/config.yaml` (single file)
- **NEW**: `~/.ubidots_cli/profiles/<profile-name>.yaml` (one file per profile)
- **MIGRATION**: Automatic - existing configs migrated on first use

### ✨ New Features

#### **Global Profile Support**

All remote commands now support `--profile` option:

```bash
# Use specific profile for any command
ubidots devices list --profile production
ubidots variables get --id 123 --profile staging
ubidots functions push --profile development
```

#### **Enhanced Configuration**

```bash
# Set default profile
ubidots config --default myprofile

# Create profile non-interactively
ubidots config --no-interactive --profile prod --token xxx --domain https://api.ubidots.com

# Create profile interactively (default behavior)
ubidots config
```

### 🐛 Bug Fixes

#### **Functions**

- Fixed: `pull` command creating nested directories instead of extracting to current directory
- Fixed: `init` command now prevents running inside existing function directories
- Fixed: Better error messages when stopping non-running functions
- Fixed: Remote function operations (add/pull) throwing errors

#### **Variables**

- Fixed: Synthetic variable creation and update operations
- Fixed: Variable validation and error handling

#### **General**

- Fixed: `--page` and `--page-size` parameter descriptions were swapped in list commands
- Fixed: Profile validation and error reporting

### 📚 Documentation

- **Complete README rewrite**: Added comprehensive examples and usage patterns for all commands
- **Better help text**: Improved command descriptions and parameter explanations
- **Profile documentation**: Complete guide for multi-environment workflows
