<!-- markdownlint-disable MD013 -->
# Ubidots CLI

Ubidots CLI is a command-line tool to build IoT applications — from raw sensor data to production-ready dashboards — using your local AI coding assistant and the Ubidots platform.

## What this is

The Ubidots CLI connects your local development environment to the Ubidots IoT platform. When paired with an AI coding assistant (Claude Code, GitHub Copilot, Codex, Cursor), it creates a tight feedback loop: write code locally, push to Ubidots, trigger it, read the logs, iterate — without leaving your terminal.

The CLI caters to both types of IoT application developers:

- **Pure backend** — Use Ubidots as your data processing and storage layer. Leverage its built-in capabilities:
  - **Device management** — Devices, device groups, and device types.
  - **Data management** — Industry-proven time-series storage and retrieval at scale; events/rules engine; hybrid hot/cold storage for 10+ years of efficient retention; PDF/XLS reporting; Data APIs for querying and transforming time-series; synthetic variables; outbound data pipelines; and more.
  - **Serverless computing** — Deploy Python or Node.js serverless functions to customize your backend. Ingest data from devices (HTTP / MQTT / CoAP), run transformations, call external APIs, apply business logic, or run ML models — Ubidots handles the data infrastructure.

- **Full-stack IoT application** — Combine all of the above with Ubidots dashboards: use pre-built widgets, drop in custom HTML/JS widgets, or build entire UIs with Ubidots Pages (HTML/JS/CSS pages embedded directly in the platform). Go from sensor data to a production UI without deploying any servers.

```text
Devices → Ubidots (data + events + APIs) → UbiFunctions (custom logic) → Pages (UI)
```

---

## Requirements

- Python 3.9+
- An Ubidots account with Industrial license or above

> *Docker is only needed if you use `ubidots functions dev` or `ubidots pages dev` (the local development environments — an optional, advanced workflow). Cloud-only workflows do not need Docker.*

## Installation

```bash
pip install ubidots-cli
ubidots --help
```

---

## Authentication

All commands that talk to Ubidots require a profile. Create one with your API token:

```bash
# Interactive setup
ubidots config

# Non-interactive (useful in scripts or CI)
ubidots config --no-interactive --profile prod --token BBFF-your-token-here

# Set as default so you don't need --profile on every command
ubidots config --default prod
```

Profiles are stored at `~/.ubidots_cli/profiles/<profile-name>.yaml`.

---

## UbiFunctions

UbiFunctions are serverless Python or Node.js functions triggered by HTTP, MQTT, or a scheduler. They can read and write device data, call external APIs, process payloads, and return responses.

### The development loop

```text
write code → push → run → logs → (iterate)
```

#### 1. Create a function and write your code

Create a remote function and pull it down to edit locally:

```bash
ubidots functions add my-function --runtime python3.11:lite
ubidots functions pull --remote-id <function-id>
cd my-function
# Write your logic in main.py (or main.js)
```

Or, if the function already exists in Ubidots:

```bash
ubidots functions pull --remote-id <function-id>
cd <function-name>
```

#### 2. Push to Ubidots

```bash
ubidots functions push
```

#### 3. Trigger and inspect logs

```bash
# Trigger with a payload and immediately print execution logs
ubidots functions run --label my-function --payload '{"value": 42}' --logs

# Show logs for the last 5 activations (default)
ubidots functions logs --label my-function

# Show logs for the last 3 activations
ubidots functions logs --label my-function --tail 3
```

### Managing functions in the cloud

```bash
# List all functions
ubidots functions list

# Get details (including the webhook URL)
ubidots functions get --label my-function --fields url,id,label,serverless,triggers --format json

# Update runtime or configuration
ubidots functions update --label my-function --runtime python3.11:base --timeout 30

# Delete
ubidots functions delete --label my-function --yes
```

### Optional: local runtime with Docker

For most workflows, pushing to Ubidots and using `functions run --logs` is the fastest feedback loop. The CLI also ships a Docker-based local runtime for the cases where you need to run against the **exact production runtime libraries** before deploying — for example, when the function depends on a specific library version and you cannot use a separate staging function in Ubidots.

This is an advanced workflow; most users will not need it.

```bash
# Scaffold a local project with a Docker-based runtime
ubidots functions dev add --name my-function --language python --runtime python3.11:lite
cd my-function

# Start the local server (requires Docker running)
ubidots functions dev start
# Prints a local URL with a dynamically assigned port — use the printed URL
curl -X POST http://localhost:<PORT> -H "Content-Type: application/json" -d '{"value": 42}'

# Tail local logs
ubidots functions dev logs --follow

# Stop when done
ubidots functions dev stop
```

---

## Ubidots Pages

Pages are custom dashboard views embedded in the Ubidots platform. Each page is an HTML/JS/CSS project that runs inside Ubidots and has access to the Ubidots JS SDK — giving it direct access to your device data.

### The development loop

```text
write HTML/JS/CSS → push → preview in Ubidots
```

#### 1. Create a page and write your code

```bash
ubidots pages add "Fleet Monitor"
ubidots pages pull --remote-id <page-id>
cd fleet-monitor
# Edit body.html, script.js, style.css using the Ubidots JS SDK
```

Or pull an existing remote page:

```bash
ubidots pages pull --remote-id <page-id>
cd <page-name>
```

#### 2. Push to Ubidots

```bash
ubidots pages push
```

The page is now live inside the Ubidots platform — open it from the Ubidots UI to preview.

### Managing pages in the cloud

```bash
# List all pages
ubidots pages list

# Get details (including the live URL)
ubidots pages get --label fleet-monitor --fields id,label,url --format json

# Update the display name
ubidots pages update --label fleet-monitor --new-name "Fleet Monitor v2"

# Delete
ubidots pages delete --label fleet-monitor --yes
```

### Optional: local preview server

For rapid iteration, you can run a local preview server with hot reload (requires Docker running):

```bash
ubidots pages dev add --name "Fleet Monitor" --type dashboard
cd "Fleet Monitor"
ubidots pages dev start
# Prints the local URL — edits to your files are reflected immediately
ubidots pages dev stop
```

This is convenient but not required — pushing and previewing inside Ubidots is always an option.

---

## Devices and Variables

```bash
# Create a device
ubidots devices add plant-sensor --name "Plant Sensor A" --tags climate,plantA

# List devices with a specific tag
ubidots devices list --filter "tags__contains=plantA" --format json

# Get a device
ubidots devices get --label plant-sensor --fields id,label,lastActivity,variables

# Create a variable on a device
ubidots variables add ~plant-sensor temperature "Temperature" --unit "°C"

# List variables in JSON
ubidots variables list --fields id,label,lastValue,unit --format json
```

---

## Typical application build — end to end

Below is the sequence an AI assistant would follow to build a complete IoT application on Ubidots from scratch.

### Step 1 — Authenticate

```bash
ubidots config --no-interactive --profile prod --token BBFF-your-token
```

### Step 2 — Build the backend function

```bash
# Create the function in Ubidots, then pull it down to edit
ubidots functions add data-processor --runtime python3.11:lite --profile prod
ubidots functions pull --remote-id <id> --profile prod
cd data-processor
# Write your logic in main.py
ubidots functions push --yes --profile prod
```

### Step 3 — Verify deployment

```bash
ubidots functions run --label data-processor --payload '{"deviceLabel": "sensor-1", "value": 22.5}' --logs --profile prod
```

### Step 4 — Build the frontend page

```bash
cd ..
ubidots pages add "Sensor Dashboard" --profile prod
ubidots pages pull --remote-id <id> --profile prod
cd sensor-dashboard
# Edit body.html, script.js, style.css using the Ubidots JS SDK
ubidots pages push --yes --profile prod
# Preview inside Ubidots
```

### Step 5 — Iterate

```bash
# Check what's running in production
ubidots functions logs --label data-processor --tail 5 --profile prod

# Pull a function down to fix a bug, edit, push
ubidots functions pull --remote-id <id> --profile prod
cd data-processor
# Fix the code
ubidots functions push --yes --profile prod
ubidots functions run --label data-processor --payload '{...}' --logs --profile prod
```

> *Need to test against the exact production runtime before pushing? See the [optional Docker local runtime](#optional-local-runtime-with-docker) under UbiFunctions.*

---

## Profiles and multi-environment workflows

Every cloud command uses your default profile (set by `ubidots config --default <name>`). The `--profile` flag lets you override that for a single command — useful when managing multiple environments (e.g. `staging`, `prod`) without changing your default.

```bash
ubidots config --no-interactive --profile staging --token BBFF-staging-token
ubidots config --no-interactive --profile prod --token BBFF-prod-token
ubidots config --default staging

# Override for a single command
ubidots functions push --profile prod
```

---

## Function runtimes

| Runtime | Description |
|---|---|
| `python3.11:lite` | Python 3.11 — minimal dependencies |
| `python3.11:base` | Python 3.11 — common data/HTTP libraries |
| `python3.11:full` | Python 3.11 — full scientific stack |
| `python3.9:lite` | Python 3.9 — minimal |
| `python3.9:base` | Python 3.9 — common libraries |
| `python3.9:full` | Python 3.9 — full stack |
| `nodejs20.x:lite` | Node.js 20 — minimal (default) |
| `nodejs20.x:base` | Node.js 20 — common libraries |

---

## Command reference

```text
ubidots config                        Set up authentication profiles
ubidots functions dev add             Create a local function project
ubidots functions dev start           Start the local function server
ubidots functions dev stop            Stop the local function server
ubidots functions dev restart         Restart the local function server
ubidots functions dev status          Check local server status
ubidots functions dev logs            Stream local logs
ubidots functions dev clean           Remove local containers and images
ubidots functions push                Upload local code to Ubidots
ubidots functions pull                Download remote function to local
ubidots functions run                 Trigger a remote function
ubidots functions logs                View remote activation logs
ubidots functions list                List all remote functions
ubidots functions get                 Get details for a remote function
ubidots functions add                 Create a new remote function
ubidots functions update              Update a remote function
ubidots functions delete              Delete a remote function
ubidots pages dev add                 Create a local page project
ubidots pages dev start               Start the local page preview server
ubidots pages dev stop                Stop the local page server
ubidots pages dev restart             Restart the local page server
ubidots pages dev status              Check page server status
ubidots pages dev list                List all local page containers
ubidots pages dev logs                Stream local page server logs
ubidots pages push                    Upload local page to Ubidots
ubidots pages pull                    Download remote page to local
ubidots pages list                    List all remote pages
ubidots pages get                     Get details for a remote page
ubidots pages add                     Create a new remote page
ubidots pages update                  Update a remote page
ubidots pages delete                  Delete a remote page
ubidots devices list                  List devices
ubidots devices get                   Get device details
ubidots devices add                   Create a device
ubidots devices update                Update a device
ubidots devices delete                Delete a device
ubidots variables list                List variables
ubidots variables get                 Get variable details
ubidots variables add                 Create a variable on a device
ubidots variables update              Update a variable
ubidots variables delete              Delete a variable
```

All commands support `--help` for full option details.
