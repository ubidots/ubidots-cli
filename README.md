# Ubidots CLI – Documentation

## Index

1. [Overview](#overview)
2. [Requirements](#requirements)
3. [Installation](#installation)
4. [Available Commands](#available-commands)
5. [Configuration (`ubidots config`)](#ubidots-config)
6. [Device Management (`ubidots devices`)](#ubidots-devices)
7. [Variable Management (`ubidots variables`)](#ubidots-variables)
8. [Function Management (`ubidots functions`)](#ubidots-functions--remote-crud)

## Overview

The Ubidots command line interface (CLI) provides:

1. A fully-featured local development environment for UbiFunctions, replicating runtimes and their
   included libraries, enabling developers to seamlessly write, test, and deploy serverless functions
   directly from their local machine.
2. CRUD (Create, Read, Update, Delete) operations for the following entities in Ubidots:
   - Devices
   - Variables
   - Functions

## Requirements

### For CRUD operations via API

- [Python 3.9 or higher (3.13 and 3.14 supported)](https://www.python.org/)

### For local UbiFunctions development

- [Docker](https://docs.docker.com/engine/install/ubuntu/)
- [Ubidots Industrial license and above](https://ubidots.com/pricing)

## Installation

```bash
pip install ubidots-cli
```

Verify installation:

```bash
ubidots --help
```

## Available Commands

- `config`: Configures essential CLI settings required for proper operation.
- `devices`: Provides CRUD functionality over Ubidots devices.
- `variables`: Provides CRUD functionality over Ubidots variables.
- `functions`: Provides CRUD functionality over UbiFunctions as well as the capability to set up a
  local development environment for UbiFunctions.

**Clarification on `--profile` flag**: All commands that interact with the remote server
(i.e. devices, variables, functions) support the `--profile` option.

If provided, the CLI will use the specified profile only for that specific command.
This does not change or affect the default profile configured in the CLI.
If `--profile` is not passed, the command will use the currently configured default profile.

## `ubidots config`

Configures the CLI cloud settings required to connect with the remote server. This command
**must be run before any other command** to ensure proper authentication.

A configuration profile includes:

- Access token for authentication
- API domain (default: `https://industrial.api.ubidots.com`)
- Auth method (default: `TOKEN`)
- A profile name used to reference these settings

You can create or update profiles either **interactively** or **non-interactively**, and you can
also **set a profile as default**.

Once created, all profiles are stored at:

```bash
$HOME/.ubidots_cli/profiles/<profile-name>.yaml
```

You can inspect them using:

```bash
cat $HOME/.ubidots_cli/profiles/myProfile.yaml
```

Example profile file:

```yaml
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
```

### Create a Profile (Interactive)

#### Description

Creates a new configuration profile by prompting the user for the required inputs.
This is the recommended method for first-time setup.

#### Command

```bash
ubidots config
```

#### Prompts

- Profile name
- API Domain (defaults to `https://industrial.api.ubidots.com`)
- Authentication method (`TOKEN` by default)
- Access token (required)

### Create a Profile (Non-Interactive)

#### Description

Creates or updates a profile by passing all parameters as flags.
Useful in scripts or CI pipelines.

#### Command

```bash
ubidots config \
  --no-interactive \
  --profile <profile-name> \
  --token <access-token>
  [--api-domain <api-domain>]
  [--auth-method TOKEN]
```

### Set a Default Profile

#### Description

Marks an existing profile as the default one. Other commands will use it if no `--profile`
is explicitly passed.

#### Command

```bash
ubidots config --default <profile-name>
```

## `ubidots devices`

Manage Ubidots devices: create, retrieve, update, delete, and list.

### Create a Device

```bash
ubidots devices add <device-label> \
  [--name "Main sensor"] \
  [--description "Sensor in Plant A"] \
  [--tags climate,plantA] \
  [--profile myProfile]
```

#### Options

- `--name`: A human-readable name for the device
- `--description`: A detailed description of the device
- `--tags`: Comma-separated list of tags to categorize the device
- `--organization`: The organization to assign the device to (use `~` prefix for organization label)
- `--properties`: Device properties in JSON format as:
  ```JSON
  "{\"prop-1\" : \"value-1\", \"prop-2\" : \"value-2\"}"
  ```
- `--profile`: Profile to use for this command

#### Assigning to an Organization

You can assign a device to an organization using either the organization's label or ID:

- Using organization label (prefix with `~`):

  ```bash
  ubidots devices add <device-label> --organization ~<organization-label>
  ```

- Using organization ID (no prefix needed):

  ```bash
  ubidots devices add <device-label> --organization <organization-id>
  ```

### Get a Device

```bash
ubidots devices get --label <device-label> [--fields <field-1,field-2,field-3>] [--format table|json]
```

#### Options

- `--label`: The label of the device to retrieve
- `--id`: The ID of the device to retrieve (alternative to `--label`)
- `--fields`: Comma-separated list of fields to include in the response. Default: `id,label,name`
  - Available fields: id, label, name, createdAt, description, isActive, lastActivity,
    organization, location, tags, url, variables, variablesCount, properties
  - Visit the [Ubidots Device Object documentation](https://docs.ubidots.com/reference/device-object)
    for more details.
- `--format`: Output format, either `table` (default) or `json`
- `--profile`: Profile to use for this command

You can retrieve a device using either its label or ID:

- Using label:

  ```bash
  ubidots devices get --label <device-label> [--fields <field-1,field-2,field-3>] [--format table|json]
  ```

- Using ID:

  ```bash
  ubidots devices get --id <device-id> [--fields <field-1,field-2,field-3>] [--format table|json]
  ```

Visit the [Ubidots Device Object documentation](https://docs.ubidots.com/reference/device-object)
for more details on available fields.

### Update a Device

```bash
ubidots devices update
  --label <device-label> \
  [--new-label <new-device-label>] \
  [--new-name <new-device-name>] \
  [--description <new-device-description>]
  [--organization <new-organization-id>] \
  [--tags <tag-1,tag-2,tag-3>] \
  [--properties <new-device-properties>]
  [--profile myProfile]
```

#### Options

- `--label`: The label of the device to update
- `--id`: The ID of the device to update (alternative to `--label`)
- `--new-label`: New label for the device
- `--new-name`: New name for the device
- `--description`: New description for the device
- `--organization`: New organization for the device (use `~` prefix for organization label)
- `--tags`: New comma-separated list of tags for the device
- `--properties`: New device properties in JSON format
- `--profile`: Profile to use for this command

**Note:**

- You can identify the device to update using either `--label <device-label>` or `--id <device-id>`
- For the `--organization` parameter, you can use either:
  - Organization label with `~` prefix: `--organization ~<org-label>`
  - Organization ID directly: `--organization <org-id>`
- **Important**: Updates replace existing values completely rather than merging them. For example:
  - If a device currently has tags `tag-1,tag-2,tag-3` and you update with `--tags other-tag`,
    the device will have only `other-tag` afterward, not all four tags.
  - To preserve existing tags while adding new ones, you must include all desired tags in the
    update command.

### Delete a Device

You can delete a device using either its label or ID:

- Using label:

  ```bash
  ubidots devices delete --label <device-label> [--profile myProfile]
  ```

- Using ID:

  ```bash
  ubidots devices delete --id <device-id> [--profile myProfile]
  ```

#### Options

- `--label`: The label of the device to delete
- `--id`: The ID of the device to delete (alternative to `--label`)
- `--profile`: Profile to use for this command

### List Devices

```bash
ubidots devices list \
  [--fields <field-1,field-2,field-3>] \
  [--filter <filter-expression>] \
  [--sort-by <attribute>] \
  [--page-size <items-per-page>] \
  [--page <page-number>] \
  [--format table|json] \
  [--profile <profile-name>]
```

#### Options

- `--fields`: Comma-separated list of fields to include in the response. Default: `id,label,name`
  - Available fields: id, label, name, createdAt, description, isActive, lastActivity,
    organization, location, tags, url, variables, variablesCount, properties
  - For more details, visit the
    [Ubidots Device Object documentation](https://docs.ubidots.com/reference/device-object)

- `--filter`: Filter results by attributes
  - Format: `key1=value1&key2__in=value2,value3` or `key1=value1\&key2__in=value2,value3`
  - Example: `--filter "tags__contains=plantA"` to find devices with the tag "plantA"
  - For more details, visit the
    [Ubidots Field Filters documentation](https://docs.ubidots.com/reference/field-filters)

- `--sort-by`: Attribute to sort the result set by (e.g., `createdAt`)

- `--page-size`: Number of items per page

- `--page`: Page number to retrieve

- `--format`: Output format, either `table` (default) or `json`

- `--profile`: Profile to use for this command

#### Examples

```bash
# List devices with tag "plantA"
ubidots devices list --filter "tags__contains=plantA"

# List devices sorted by creation date
ubidots devices list --sort-by createdAt

# List devices with custom fields in JSON format
ubidots devices list --fields id,label,tags,lastActivity --format json
```

## `ubidots variables`

Manage variables associated with a device: create, retrieve, update, delete, and list.

### Create a Variable

```bash
ubidots variables add \
  <device> \
  <variable-label> \
  [<variable-name>] \
  [--unit <unit>] \
  [--type raw|synthetic] \
  [--tags <tag1,tag2,tag3>] \
  [--profile <profile>]
```

#### Arguments

- `device`: The device associated with the variable (required)
  - Use device label with `~` prefix: `~device-label`
  - Use device ID directly: `device-id`
- `variable-label`: The label for the variable
- `variable-name`: The name of the variable

#### Options

- `--description`: A brief description of the variable
- `--type`: The type of variable (`raw` or `synthetic`, default: `raw`)
- `--unit`: The unit of measurement for the variable
- `--synthetic-expression`: Expression used to calculate the value (for synthetic variables)
- `--tags`: Comma-separated tags for the variable
- `--properties`: Variable properties in JSON format
- `--min`: Lowest value allowed
- `--max`: Highest value allowed
- `--profile`: Profile to use for this command

#### Examples

##### Create a raw variable using device label

```bash
ubidots variables add ~plant-sensor humidity "Humidity" --unit % --type raw
```

##### Create a synthetic variable

```bash
ubidots variables add ~plant-sensor temp-f "Temperature (F)" \
  --type synthetic \
  --synthetic-expression "mean( ((9 / 5) * {{68122b4ae1717c43f7ad41e5}}) + 32, \"10T\" )"
```

Visit the [Ubidots Synthetic Variables documentation](https://help.ubidots.com/en/articles/1767999-analytics-synthetic-variables-basics)
for more details on synthetic variables and valid expressions.

### Get a Variable

```bash
ubidots variables get --id <variable-id> [--fields <field-1,field-2,field-3>] [--format table|json]
```

#### Options

- `--id`: Unique identifier for the variable (required)
- `--fields`: Comma-separated list of fields to include in the response. Default: `id,label,name`
  - Available fields: id, label, name, createdAt, syntheticExpression, description, device,
    lastActivity, lastValue, properties, tags, type, unit, url, valuesUrl
  - Visit the [Ubidots Variable Object documentation](https://docs.ubidots.com/reference/variable-object)
    for more details.
- `--format`: Output format, either `table` (default) or `json`
- `--profile`: Profile to use for this command

#### Example

Get variable details with custom fields in JSON format

```bash
ubidots variables get --id 64abcdeff00 --fields id,label,lastValue,unit --format json
```

### Update a Variable

```bash
ubidots variables update --id <variable-id> \
  [--new-label <new-label>] \
  [--new-name <new-name>] \
  [--description <description>] \
  [--type raw|synthetic] \
  [--unit <unit>] \
  [--tags <tag1,tag2,tag3>] \
  [--profile <profile>]
```

#### Options

- `--id`: Unique identifier for the variable (required)
- `--new-label`: New label for the variable
- `--new-name`: New name for the variable
- `--description`: New description for the variable
- `--type`: The type of variable (`raw` or `synthetic`, default: `raw`)
- `--unit`: New unit of measurement for the variable
- `--synthetic-expression`: New expression used to calculate the value (for synthetic variables)
- `--tags`: New comma-separated tags for the variable
- `--properties`: New variable properties in JSON format
- `--min`: New lowest value allowed
- `--max`: New highest value allowed
- `--profile`: Profile to use for this command

**Important**: Updates replace existing values completely rather than merging them. For example:

- If a variable currently has tags `tag-1,tag-2,tag-3` and you update with `--tags other-tag`,
  the variable will have only `other-tag` afterward, not all four tags.
- To preserve existing tags while adding new ones, you must include all desired tags in the
  update command.

#### Example

```bash
# Update a variable's name and unit
ubidots variables update --id 64abcdeff00 --new-name "New Temperature" --unit "°F"
```

### Delete a Variable

```bash
ubidots variables delete --id <variable-id> [--profile <profile-name>]
```

#### Options

- `--id`: Unique identifier for the variable (required)
- `--profile`: Profile to use for this command

#### Example

```bash
ubidots variables delete --id 64abcdeff00 [--profile myProfile]
```

### List Variables

```bash
ubidots variables list \
  [--fields <field-1,field-2,field-3>] \
  [--filter <filter-expression>] \
  [--sort-by <attribute>] \
  [--page-size <items-per-page>] \
  [--page <page-number>] \
  [--format table|json] \
  [--profile <profile-name>]
```

#### Options

- `--fields`: Comma-separated list of fields to include in the response. Default: `id,label,name`
  - Available fields: id, label, name, createdAt, syntheticExpression, description, device,
    lastActivity, lastValue, properties, tags, type, unit, url, valuesUrl
  - For more details, visit the
    [Ubidots Variable Object documentation](https://docs.ubidots.com/reference/variable-object)

- `--filter`: Filter results by attributes
  - Format: `key1=value1&key2__in=value2,value3` or `key1=value1\&key2__in=value2,value3`
  - Example: `--filter "type=raw"` to find only raw variables
  - For more details, visit the
    [Ubidots Field Filters documentation](https://docs.ubidots.com/reference/field-filters)

- `--sort-by`: Attribute to sort the result set by (e.g., `createdAt`)

- `--page-size`: Number of items per page

- `--page`: Page number to retrieve

- `--format`: Output format, either `table` (default) or `json`

- `--profile`: Profile to use for this command

#### Examples

```bash
# List all raw variables
ubidots variables list --filter "type=raw"

# List variables with custom fields in JSON format
ubidots variables list --fields id,label,lastValue,unit --format json

# List variables sorted by creation date
ubidots variables list --sort-by createdAt
```

## `ubidots functions` – Remote CRUD

Manage UbiFunctions remotely on the Ubidots platform: create, retrieve, update, delete, and list.

### Create a Remote Function

```bash
ubidots functions add "Function from CLI" \
  [--runtime <runtime>] \
  [--timeout <timeout>] \
  [--raw] \
  [--methods GET] \
  [--methods POST] \
  [--cors] \
  [--environment '[{"key": "value"}]'] \
  [--profile myProfile]
```

#### Arguments

- `name`: The name of the function (required)

#### Options

- `--label`: The label for the function (if not provided, a sanitized version of the name will
  be used)
- `--runtime`: The runtime environment for the function. Available options:
  - Default: `nodejs20.x:lite`
  - Python:
    - `python3.9:lite`
    - `python3.9:base`
    - `python3.9:full`
    - `python3.11:lite`
    - `python3.11:base`
    - `python3.11:full`
  - Node.js:
    - `nodejs20.x:lite`
    - `nodejs20.x:base`
- `--timeout`: Timeout for the function in seconds (default: 10)
- `--raw`: Flag to determine if the output should be in raw format
- `--methods`: The HTTP methods the function will respond to (can be specified multiple times)
  - Available options: `GET`, `POST`
  - Default: `GET`
- `--cors`: Flag to enable Cross-Origin Resource Sharing (CORS) for the function
- `--environment`: Environment variables in JSON format (default: `[]`)
- `--profile`: Profile to use for this command

#### Example

```bash
# Create a Python function with multiple HTTP methods
ubidots functions add "Temperature Converter" \
  --label temp-converter \
  --runtime python3.11:base \
  --methods GET \
  --methods POST \
  --cors \
  --environment "[{\"label\": \"debug\", \"type\": \"global-property\"}]" \
  --profile myProfile
```

**Note about environment variables:**
The `--environment` parameter accepts a JSON array of objects as a string with escaped quotes.
Each object should reference environment variables that already exist in the platform.
The format is:

```json
"[{\"label\": \"<global-property-label>\", \"type\": \"global-property\"}]"
```

### Get a Remote Function

```bash
ubidots functions get [--id <function-id>] [--label <function-label>] \
  [--fields <field-1,field-2,field-3>] \
  [--format table|json] \
  [--profile <profile-name>] \
  [--verbose]
```

#### Options

- `--id`: Unique identifier for the function
- `--label`: The label of the function (alternative to `--id`)
- `--fields`: Comma-separated list of fields to include in the response. Default: `id,label,name`
  - Available fields: url, id, label, name, isActive, createdAt, serverless, triggers,
    environment, zipFileProperties
- `--format`: Output format, either `table` (default) or `json`
- `--profile`: Profile to use for this command
- `--verbose`: Enable verbose output

#### Example

```bash
# Get function details with custom fields in JSON format
ubidots functions get --label temp-converter --fields id,label,serverless --format json
```

### Update a Remote Function

```bash
ubidots functions update [--id <function-id>] [--label <function-label>] \
  [--new-label <new-function-label>] \
  [--new-name <new-function-name>] \
  [--runtime <runtime>] \
  [--raw] \
  [--cors] \
  [--timeout <timeout-seconds>] \
  [--methods GET] [--methods POST] \
  [--environment <environment-json>] \
  [--profile <profile-name>] \
  [--verbose]
```

#### Options

- `--id`: Unique identifier for the function
- `--label`: The label of the function (alternative to `--id`)
- `--new-label`: New label for the function
- `--new-name`: New name for the function
- `--runtime`: New runtime for the function (see available options in the
  [Create a Remote Function](#create-a-remote-function) section)
- `--raw`: Flag to determine if the output should be in raw format
- `--cors`: Flag to enable Cross-Origin Resource Sharing (CORS)
- `--timeout`: New timeout for the function in seconds
- `--methods`: The HTTP methods the function will respond to (can be specified multiple times)
- `--environment`: New environment variables in JSON format
- `--profile`: Profile to use for this command
- `--verbose`: Enable verbose output

#### Example

```bash
ubidots functions update --label temp-converter \
  --new-label "temp-converter-v2" \
  --new-name "Temperature Converter v2" \
  --runtime python3.11:base \
  --timeout 30 \
  --raw \
  --methods GET --methods POST \
  --cors \
  --environment "[{\"label\": \"debug\", \"type\": \"global-property\"}]"
```

**Note about environment variables:**
The `--environment` parameter accepts a JSON array of objects as a string with escaped quotes.
Each object should reference environment variables that already exist in the platform.
The format is:

```json
"[{\"label\": \"<global-property-label>\", \"type\": \"global-property\"}]"
```

**Important**: Updates replace existing values completely rather than merging them. To preserve
existing settings while updating others, you should include all desired settings in the update
command.

### Delete a Remote Function

```bash
ubidots functions delete [--id <function-id>] [--label <function-label>] \
  [--profile <profile-name>] \
  [--yes] \
  [--verbose]
```

#### Options

- `--id`: Unique identifier for the function (takes precedence if both `--id` and `--label`
  are provided)
- `--label`: The label of the function (used only if `--id` is not provided)
- `--profile`: Profile to use for this command
- `--yes`: Confirm deletion without prompt (`-y` for short)
- `--verbose`: Enable verbose output

#### Example

```bash
# Delete a function without confirmation prompt
ubidots functions delete --label temp-converter --yes
```

### List Remote Functions

```bash
ubidots functions list \
  [--fields <field-1,field-2,field-3>] \
  [--filter <filter-expression>] \
  [--sort-by <attribute>] \
  [--page-size <items-per-page>] \
  [--page <page-number>] \
  [--format table|json] \
  [--profile <profile-name>]
```

#### Options

- `--fields`: Comma-separated list of fields to include in the response.
  - Default: `id,label,name`
  - Available fields: url, id, label, name, isActive, createdAt, serverless, triggers,
    environment, zipFileProperties.
- `--filter`: Filter results by attributes
- `--sort-by`: Attribute to sort the result set by

- `--page-size`: Number of items per page

- `--page`: Page number to retrieve

- `--format`: Output format, either `table` (default) or `json`

- `--profile`: Profile to use for this command

#### Example

```bash
# List functions with custom fields sorted by creation date
ubidots functions list --fields id,label,createdAt --sort-by createdAt
```

## `ubidots functions` – Local UbiFunction Development

Use this set of commands to create, run, and manage local UbiFunctions via Docker.
These must be executed **inside the function directory** (e.g., `cd my_function`).

### Create a Local Function

```bash
ubidots functions init \
  [--name <function-name>] \
  [--language python|nodejs] \
  [--runtime <runtime>] \
  [--remote-id <remote-function-id>] \
  [--methods GET] [--methods POST] \
  [--raw] \
  [--cors] \
  [--token <token>] \
  [--timeout <timeout-seconds>] \
  [--cron <cron-expression>] \
  [--profile <profile-name>] \
  [--verbose]
```

#### Options

- `--name`: The name for the function (default: "my-function")
- `--language`: The programming language for the function (`python` or `nodejs`)
- `--runtime`: The runtime for the function (see available options in the
  [Create a Remote Function](#create-a-remote-function) section)
- `--remote-id`: The remote function ID to pull from server
- `--methods`: The HTTP methods the function will respond to (can be specified multiple times)
- `--raw`: Flag to enable raw mode for response output
- `--cors`: Flag to enable CORS headers in responses
- `--token`: Token for testing invocation
- `--timeout`: Timeout for the function in seconds
- `--cron`: Cron expression for scheduled execution
- `--profile`: Profile to use for this command
- `--verbose`: Enable verbose output

This command will create a local UbiFunction based on the options provided.

- `--language` and `--runtime` are required unless using `--remote-id`.
- You may also pass additional optional flags:
  - `--raw`: Enables raw mode for response output
  - `--cors`: Enables CORS headers in responses
  - `--token`: Sets a token for testing invocation
  - `--methods`: Specifies the HTTP methods the function will respond to

#### How to specify multiple HTTP methods

To declare multiple HTTP methods, repeat the `--methods` flag:

```bash
--methods GET --methods POST
```

#### Example

```bash
ubidots functions init \
  --name myFunction \
  --language nodejs \
  --runtime nodejs20.x:base \
  --methods GET --methods POST
```

#### Pull from Remote Instead

If the `--remote-id` flag is passed, the CLI will pull the function from the remote server and
recreate it locally. In this case, all other flags like `--language`, `--runtime`, `--methods`,
etc., are ignored.

```bash
ubidots functions init --remote-id 67ef05f2c9917a07b8f04519 [--profile myProfile]
```

### Start the Local Function

Launches the function locally using Docker.

```bash
ubidots functions start [--verbose]
```

#### Options

- `--verbose`: Enable verbose output

**Note for Windows users:** If you're using WSL (Windows Subsystem for Linux), ensure that Docker
Desktop is running on your Windows system before executing this command. The command will fail if
Docker is not running or not properly configured to work with WSL.

### Restart the Local Function

Restarts the local container.

```bash
ubidots functions restart [--verbose]
```

#### Options

- `--verbose`: Enable verbose output

### Stop the Local Function

Stops the local container.

```bash
ubidots functions stop [--verbose]
```

#### Options

- `--verbose`: Enable verbose output

### Check Local Function Status

Displays whether the local function is currently running.

```bash
ubidots functions status [--verbose]
```

#### Options

- `--verbose`: Enable verbose output

### View Logs

This command must be run inside a local UbiFunction directory.

```bash
ubidots functions logs \
  [--tail <number-of-lines>] \
  [--follow] \
  [--remote] \
  [--profile <profile-name>] \
  [--verbose]
```

#### Options

- `--tail`: Output specified number of lines at the end of logs
- `--follow`: Follow log output
- `--profile`: Profile to use for this command
- `--remote`: Fetch logs from the remote server instead of local execution
- `--verbose`: Enable verbose output

By default, this displays **logs from the local execution**. To fetch logs from the
**remote server instead**, use the `--remote` flag:

```bash
ubidots functions logs --remote [--profile myProfile]
```

### Push Local Changes to Remote

Uploads and synchronizes your local function code with the remote server.

```bash
ubidots functions push \
  [--confirm] \
  [--profile <profile-name>] \
  [--verbose]
```

#### Options

- `--confirm`: Confirm file overwrite without prompt (`--yes` or `-y`)
- `--profile`: Profile to use for this command
- `--verbose`: Enable verbose output

### Pull Latest Remote Changes to Local

Fetches the latest code from the remote server and creates a new directory with the function name.

```bash
ubidots functions pull \
  --remote-id <remote-function-id> \
  [--profile <profile-name>] \
  [--confirm] \
  [--verbose]
```

#### Options

- `--remote-id`: The remote function ID (required)
- `--profile`: Profile to use for this command
- `--confirm`: Confirm file overwrite without prompt (`--yes` or `-y`)
- `--verbose`: Enable verbose output

**Important directory behavior:**

- If you run this command from `/home/functions`, the function will be pulled to
  `/home/functions/function-name`
- If you run this command from `/home/functions/function-name`, it will create a nested directory
  `/home/functions/function-name/function-name`

It is recommended to always run this command from the parent directory where you want the function
to be created, not from within an existing function directory.
