# Ubidots CLI – Documentation

## Index

1. [Overview](#overview)
2. [Requirements](#requirements)
3. [Installation](#installation)
4. [Available Commands](#available-commands)
5. [Configuration (`ubidots config`)](#ubidots-config)
6. [Device Management (`ubidots devices`)](#ubidots-devices)
7. [Variable Management (`ubidots variables`)](#ubidots-variables)
8. [Function Management (`ubidots functions`)](#ubidots-functions)
9. [Configuration File Location](#configuration-file-location)


# Overview

The Ubidots command line interface (CLI) provides:

1. A fully-featured local development environment for UbiFunctions, replicating runtimes and their included libraries, enabling developers to seamlessly write, test, and deploy serverless functions directly from their local machine.
2. CRUD (Create, Read, Update, Delete) operations for the following entities in Ubidots:
   - Devices
   - Variables
   - Functions


# Requirements

## For CRUD operations via API
- <a href="https://www.python.org/">Python 3.12.2 or higher</a>

## For local UbiFunctions development
- <a href="https://docs.docker.com/engine/install/ubuntu/">Docker</a>
- <a href="https://ubidots.com/pricing">Ubidots Industrial license and above</a>


# Installation

<pre><code>pip install ubidots-cli</code></pre>

Verify installation:

<pre><code>ubidots --help</code></pre>


# Available Commands

- `config`: Configures essential CLI settings required for proper operation.
- `devices`: Provides CRUD functionality over Ubidots devices.
- `variables`: Provides CRUD functionality over Ubidots variables.
- `functions`: Provides CRUD functionality over UbiFunctions as well as the capability to set up a local development environment for UbiFunctions.

**Clarification on `--profile` flag**: All commands that interact with the remote server (i.e. devices, variables, functions) support the `--profile` option. 

If provided, the CLI will use the specified profile only for that specific command.
This does not change or affect the default profile configured in the CLI.
If `--profile` is not passed, the command will use the currently configured default profile.



# `ubidots config`

Configures the CLI cloud settings required to connect with the remote server. This command **must be run before any other command** to ensure proper authentication.

A configuration profile includes:
- Access token for authentication
- API domain (default: `https://industrial.api.ubidots.com`)
- Auth method (default: `TOKEN`)
- A profile name used to reference these settings

You can create or update profiles either **interactively** or **non-interactively**, and you can also **set a profile as default**.

Once created, all profiles are stored at:

<pre><code>$HOME/.ubidots_cli/profiles/&lt;profile-name&gt;.yaml</code></pre>

You can inspect them using:

<pre><code>cat $HOME/.ubidots_cli/profiles/myProfile.yaml</code></pre>

Example profile file:

<pre><code>
access_token: BBFF-XXYYZZ
api_domain: https://industrial.api.ubidots.com
auth_method: X-Auth-Token
containerRepositoryBase: https://registry.hub.docker.com/library/
runtimes:
- python3.9:full
- python3.9:lite
- python3.9:base
- python3.11:full
- python3.11:lite
- python3.11:base
- nodejs20.x:lite
- nodejs20.x:base
</code></pre>

## Create a Profile (Interactive)

### Description

Creates a new configuration profile by prompting the user for the required inputs. This is the recommended method for first-time setup.

### Command

<pre><code>ubidots config</code></pre>

### Prompts

- Profile name
- API Domain (defaults to `https://industrial.api.ubidots.com`)
- Authentication method (`TOKEN` by default)
- Access token (required)


## Create a Profile (Non-Interactive)

### Description

Creates or updates a profile by passing all parameters as flags. Useful in scripts or CI pipelines.

### Command

<pre><code>
ubidots config \
  --no-interactive \
  --profile myProfile \
  --token BBFF-xyz
</code></pre>

### Optional flags

<pre><code>
--api-domain https://industrial.api.ubidots.com
--auth-method TOKEN
</code></pre>


## Set a Default Profile

### Description

Marks an existing profile as the default one. Other commands will use it if no `--profile` is explicitly passed.

### Command

<pre><code>ubidots config --default myProfile</code></pre>


# `ubidots devices`
Manage Ubidots devices: create, retrieve, update, delete, and list.

## Create a Device
<pre><code>
ubidots devices add my-device \
  --name "Main sensor" \
  --description "Sensor in Plant A" \
  --tags climate,plantA \
  [--profile myProfile]
</code></pre>

## Get a Device
<pre><code>
ubidots devices get --label my-device [--profile myProfile]
</code></pre>

## Update a Device

<pre><code>ubidots devices update --label my-device \
  --new-name "Updated name" \
  --tags updated,tag \
  [--profile myProfile]
</code></pre>

## Delete a Device

<pre><code>
ubidots devices delete --label my-device [--profile myProfile]
</code></pre>

## List Devices

<pre><code>
ubidots devices list \
  --filter "tags=plantA" \
  --sort-by createdAt \
  [--profile myProfile]
</code></pre>

# `ubidots variables`

Manage variables associated with a device: create, retrieve, update, delete, and list.

## Create a Variable

<pre><code>
ubidots variables add ~label=my-device tempSensor "Temperature" \
  --unit °C \
  --type raw \
  --tags temp,env \
  [--profile myProfile]
</code></pre>

## Get a Variable

<pre><code>
ubidots variables get --id 64abcdeff00 [--profile myProfile]
</code></pre>

## Update a Variable

<pre><code>
ubidots variables update --id 64abcdeff00 \
  --new-name "New Name" \
  --unit °F \
  --tags updated \
  [--profile myProfile]
</code></pre>

## Delete a Variable

<pre><code>
ubidots variables delete --id 64abcdeff00 [--profile myProfile]
</code></pre>

## List Variables

<pre><code>
ubidots variables list --filter "type=raw" [--profile myProfile]
</code></pre>

# `ubidots functions` – Remote CRUD

Manage UbiFunctions remotely on the Ubidots platform: create, retrieve, update, delete, and list.

## Create a Remote Function

<pre><code>
ubidots functions add "Function from CLI" \
  [--runtime python3.11:base] \
  [--profile myProfile]
</code></pre>

## Get a Remote Function

<pre><code>
ubidots functions get --label my-function [--profile myProfile]
</code></pre>

## Update a Remote Function

<pre><code>
ubidots functions update --label my-function \
  --new-name "Renamed" \
  [--runtime nodejs20.x:lite] \
  [--profile myProfile]
</code></pre>

## Delete a Remote Function

<pre><code>
ubidots functions delete --label my-function [--profile myProfile]
</code></pre>

## List Remote Functions

<pre><code>
ubidots functions list --fields id,label [--profile myProfile]
</code></pre>


# `ubidots functions` – Local UbiFunction Development

Use this set of commands to create, run, and manage local UbiFunctions via Docker.  
These must be executed **inside the function directory** (e.g., `cd my_function`).

## Create a Local Function

<pre><code>
ubidots functions init \
  --name myFunction \
  --language python \
  --runtime python3.11:base
</code></pre>

This command will create a local UbiFunction based on the options provided.

- `--language` and `--runtime` are required unless using `--remote-id`.
- You may also pass additional optional flags:
  - `--raw`: Enables raw mode for response output
  - `--cors`: Enables CORS headers in responses
  - `--token`: Sets a token for testing invocation
  - `--methods`: Specifies the HTTP methods the function will respond to

### How to specify multiple HTTP methods

To declare multiple HTTP methods, repeat the `--methods` flag:

<pre><code>
--methods GET --methods POST
</code></pre>

Example:

<pre><code>
ubidots functions init \
  --name myFunction \
  --language nodejs \
  --runtime nodejs20.x:base \
  --methods GET --methods POST
</code></pre>


### Pull from Remote Instead

If the `--remote-id` flag is passed, the CLI will pull the function from the remote server and recreate it locally.  
In this case, all other flags like `--language`, `--runtime`, `--methods`, etc., are ignored.

<pre><code>
ubidots functions init --remote-id 67ef05f2c9917a07b8f04519 [--profile myProfile]
</code></pre>



## Start the Local Function

Launches the function locally using Docker.

<pre><code>ubidots functions start</code></pre>

## Restart the Local Function

Restarts the local container.

<pre><code>ubidots functions restart</code></pre>

## Stop the Local Function

Stops the local container.

<pre><code>ubidots functions stop</code></pre>

## Check Local Function Status

Displays whether the local function is currently running.

<pre><code>ubidots functions status</code></pre>

## View Logs

<pre><code>ubidots functions logs</code></pre>

By default, this displays **logs from the local execution**.

To fetch logs from the **remote server instead**, use the `--remote` flag:

<pre><code>ubidots functions logs --remote [--profile myProfile]</code></pre>


## Push Local Changes to Remote

Uploads and synchronizes your local function code with the remote server.

<pre><code>ubidots functions push [--profile myProfile]</code></pre>

## Pull Latest Remote Changes to Local

Fetches the latest code from the remote server and applies it to the current local function directory.

<pre><code>ubidots functions pull --remote-id 67ef05f2c9917a07b8f04519 [--profile myProfile]</code></pre>

