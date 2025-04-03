# Ubidots CLI 
1. [Overview](#overview)
2. [Requirements](#requirements)
3. [Installation](#installation)
4. [Available commands](#available-commands)
5. [`ubidots config`](#ubidots-config)
6. [`ubidots devices`](#ubidots-devices)
7. [`ubidots variables`](#ubidots-variables)
8. [`ubidots functions`](#ubidots-functions)

# Overview 
The Ubidots command line interface (CLI) provides:
1. A fully-featured local development environment for UbiFunctions, replicating runtimes and their included libraries, enabling developers to seamlessly write, test, and deploy serverless functions directly from their local machine.
2. CRUD (Create, Read, Update, Delete) operations for the following entities in Ubidots:
   - Devices
   - Variables
   - Functions

# Requirements
## For CRUD operations via API 
- [Python 3.12.2 or higher](https://www.python.org/)
## For local UbiFunctions development
- [Docker](https://docs.docker.com/engine/install/ubuntu/) 
- [Ubidots Industrial license and above](https://ubidots.com/pricing)



# Installation
```bash
pip install ubidots-cli
```
Once installed, verify the installation by checking the help menu:
```bash
ubidots --help
```

# Available commands
- `config`: Configures essential CLI settings required for proper operation.
- `devices`: Provides CRUD functionality over Ubidots devices.
- `variables`: Provides CRUD functionality over Ubidots variables.
- `functions`: Provides CRUD functionality over UbiFunctions as well as the capability to set up a local development environment for UbiFunctions.

## `ubidots config`
Configures the CLI cloud settings required to connect with remote server. This command **must be run before any other command** to ensure proper authentication.

The command has two distinct behaviors:

- Setting a profile as default.
- Create or update an existing profile.


### 1. Setting the Default Profile
To set an existing profile as the default, use:
<pre><code>ubidots config --default &lt;profile-name&gt;</code></pre>
- This sets <code>&lt;profile-name&gt;</code> as the default profile.
- Any command that requires a profile but does not explicitly specify one will use this default.
- <strong>If the specified profile does not exist, an error will be thrown.</strong>
- <strong>Any other options provided will be ignored when using <code>--default</code>.</strong>

### 2. Creating or Updating a Profile
If the <code>--default</code> flag is not used, the command allows the creation of a new profile in <strong>interactive</strong> or <strong>non-interactive</strong> mode.

#### **Interactive Mode (Default)**
Running:
<pre><code>ubidots config</code></pre>
prompts the user to provide the following details:
- **Profile Name**: _(Mandatory)_ Must be a valid string.
- **API Domain**: _(Optional)_ Defaults to <code>https://industrial.api.ubidots.com</code>.
- **Authentication Method**: _(Optional)_ Defaults to <code>TOKEN</code>.
- **Access Token**: _(Mandatory)_ Must be a valid token with API access. If invalid, the command will fail, and the profile will not be created.

#### **Non-Interactive Mode**
To create a profile without prompts, use:
<pre><code>ubidots config \
--no-interactive \
--profile &lt;profile-name&gt; \
--token &lt;token&gt; \
--auth-method &lt;auth-method&gt \
--api-domain &lt;domain&gt;</code></pre>

- **Profile Name (<code>--profile</code>)**: _(Mandatory)_ The name of the profile.
- **Access Token (<code>--token</code>)**: _(Mandatory)_ A valid API access token.
- **API Domain (<code>--api-domain</code>)**: _(Optional)_ Defaults to <code>https://industrial.api.ubidots.com</code>.
- **Authentication Method (<code>--auth-method</code>)**: _(Optional)_ Defaults to <code>TOKEN</code>.

💡 **Note:** At least <code>--profile</code> and <code>--token</code> are required in non-interactive mode. The other two options take default values if not provided.

This configuration will be saved at `$HOME/.ubidots_cli/profiles/<profile-name>.yaml`. You can check it by running `cat`:

```bash
cat $HOME/.ubidots_cli/profiles/<profile-name>.yaml

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

# `ubidots devices`
This command allows CRUD operations over devices in Ubidots.
```bash
 Usage: ubidots devices [OPTIONS] COMMAND [ARGS]...                             
                                                                                
 Device management and operations.                                              
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ add        Adds a new device.                                                │
│ delete     Deletes a specific device using its id or label.                  │
│ get        Retrieves a specific device using its id or label.                │
│ list       Lists all available devices.                                      │
│ update     Update a device.                                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## Create a device
Create a new device on Ubidots.
```bash
 Usage: ubidots devices add [OPTIONS] LABEL                                     
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│  label      TEXT  The label for the device. [required]                       │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --name                TEXT  The name of the device.                          │
│ --description         TEXT  A brief description of the device.               │
│ --organization        TEXT  The organization associated with the device. Its │
│                             id or ['~label' | \~label].                      │
│ --tags                TEXT  Comma-separated tags for the device. e.g.        │
│                             tag1,tag2,tag3                                   │
│ --properties          TEXT  Device properties in JSON format. [default: {}]  │
│ --profile             TEXT  Profile to use.                          │
│ --help                      Show this message and exit.                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## Get a device
Retrieve a device from Ubidots.
```bash
 Usage: ubidots devices get [OPTIONS]                                           
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --id            TEXT  Unique identifier for the device. If both id and       │
│                       label are provided, the id takes precedence.           │
│ --label         TEXT  Descriptive label identifier for the device.           │
│                       Ignored if id is provided.                             │
│ --profile       TEXT  Profile to use to interact with the remote server.                                                                                                                  │
│ --fields        TEXT  Comma-separated fields to process. e.g.                │
│                       field1,field2,field3                                   │
│                       [default: id,label,name]                               │
│ --help                Show this message and exit.                            │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## Update a device
Update an existing device's settings on Ubidots. 

```bash
 Usage: ubidots devices update [OPTIONS]                                        
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --id                  TEXT  Unique identifier for the device. If both id     │
│                             and label are provided, the id takes precedence. │
│ --label               TEXT  Descriptive label identifier for the device.     │
│                             Ignored if id is provided.                       │
│ --new-label           TEXT  The label for the device.                        │
│ --new-name            TEXT  The name of the device.                          │
│ --description         TEXT  A brief description of the device.               │
│ --organization        TEXT  The organization associated with the device. Its │
│                             id or ['~label' | \~label].                      │
│ --tags                TEXT  Comma-separated tags for the device. e.g.        │
│                             tag1,tag2,tag3                                   │
│ --properties          TEXT  Device properties in JSON format. [default: {}]  │
│ --profile             TEXT  Profile to use to interact with the remote server.                                                                                                                  │
│ --help                      Show this message and exit.                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```


## Delete a device
Delete a device from your Ubidots account.

```bash
 Usage: ubidots devices delete [OPTIONS]                                        
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --id           TEXT  Unique identifier for the device. If both id and        │
│                      label are provided, the id takes precedence.            │
│ --label        TEXT  Descriptive label identifier for the device.            │
│                      Ignored if id is provided.                              │
│ --profile             TEXT  Profile to use to interact with the remote server.                                                                                                                  │
│ --help               Show this message and exit.                             │
╰──────────────────────────────────────────────────────────────────────────────╯
```
**Note**: This command permanently deletes the device, just like removing it through the platform, thus special care is advised. 


# `ubidots variables`
This command allow CRUD operations over variables in Ubidots. 
```bash
 Usage: ubidots variables [OPTIONS] COMMAND [ARGS]...                           
                                                                                
 Variable management and operations.                                            
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ add         Adds a new variable.                                             │
│ delete      Deletes a specific variable using its id                         │
│ get         Retrieves a specific variable using its id.                      │
│ list        Lists all available variables.                                   │
│ update      Update a variable.                                               │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## Create variable
Create a new variable in a given device in Ubidots.

```bash
 Usage: ubidots variables add [OPTIONS] DEVICE [LABEL] [NAME]                   
                                                                                
╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│      device      TEXT     The device associated with the variable. Its id or │
│                           ['~label'|\~label].                                │
│                           [required]                                         │
│      label       [LABEL]  The label for the variable.                        │
│      name        [NAME]   The name of the variable.                          │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --description                 TEXT             A brief description of the    │
│                                                variable.                     │
│ --type                        [raw|synthetic]  The type of variable.         │
│                                                [default: raw]                │
│ --unit                        TEXT             The unit of measurement that  │
│                                                represents the variable.      │
│ --synthetic-expression        TEXT             If the variable is of type    │
│                                                'synthetic', this is the      │
│                                                corresponding synthetic       │
│                                                expression used to calculate  │
│                                                its value.                    │
│ --tags                        TEXT             Comma-separated tags for the  │
│                                                variable. e.g. tag1,tag2,tag3 │
│ --properties                  TEXT             Device properties in JSON     │
│                                                format.                       │
│                                                [default: {}]                 │
│ --min                         INTEGER          Lowest value allowed.         │
│ --max                         INTEGER          Highest value allowed.        │
│ --profile                     TEXT             Profile to use to interact  with the remote server.                                                                                                                  │
│ --help                                         Show this message and exit.   │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## Get a variable
Retrieve a variable from Ubidots.

```bash
 Usage: ubidots variables get [OPTIONS]                                         
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│    --id            TEXT  Unique identifier for the variable. [required]      │
│ --profile          TEXT  Profile to use to interact  with the remote server.                                                                                                                  │
│    --fields        TEXT  Comma-separated fields to process. e.g.             │
│                          field1,field2,field3                                │
│                          [default: id,label,name]                            │
│    --help                Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## Update a variable
Update a variable in Ubidots.

```bash
 Usage: ubidots variables update [OPTIONS]                                      
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│    --id                          TEXT             Unique identifier for      │
│                                                   the variable.              │
│                                                   [required]                 │
│    --new-label                   TEXT             The label for the          │
│                                                   variable.                  │
│    --new-name                    TEXT             The name of the variable.  │
│    --description                 TEXT             A brief description of the │
│                                                   variable.                  │
│    --type                        [raw|synthetic]  The type of variable.      │
│                                                   [default: raw]             │
│    --unit                        TEXT             The unit of measurement    │
│                                                   that represents the        │
│                                                   variable.                  │
│    --synthetic-expression        TEXT             If the variable is of type │
│                                                   'synthetic', this is the   │
│                                                   corresponding synthetic    │
│                                                   expression used to         │
│                                                   calculate its value.       │
│    --tags                        TEXT             Comma-separated tags for   │
│                                                   the variable. e.g.         │
│                                                   tag1,tag2,tag3             │
│    --properties                  TEXT             Device properties in JSON  │
│                                                   format.                    │
│                                                   [default: {}]              │
│    --min                         INTEGER          Lowest value allowed.      │
│    --max                         INTEGER          Highest value allowed.     │
│    --profile                     TEXT             Profile to use to interact  with the remote server.                                                                                                                  │
│    --help                                         Show this message and      │
│                                                   exit.                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## Delete a variable
Delete a variable from your Ubidots account.

```bash
 Usage: ubidots variables delete [OPTIONS]                                      
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│    --id          TEXT  Unique identifier for the variable. [required]        │
│    --profile     TEXT Profile to use to interact  with the remote server.                                                                                                                  │
│    --help        Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

**Note**: This command permanently deletes the variable, just like removing it through the platform, thus special care is advised. 


# `ubidots functions`
This command allows to:
- Perform CRUD operations over UbiFunctions in Ubidots.
- Set up a local development environment featuring all the runtimes supported on UbiFunctions and their respective libraries. Docker is required for this.

```bash
 Usage: ubidots functions [OPTIONS] COMMAND [ARGS]...                                                                                                                               
 
 Tool for managing and deploying functions.                                                                                                                                                         ╭─ Options ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                                                                        │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ add         Adds a new function in the remote server.                                                                                                                                              │
│ delete      Deletes a specific function using its id or label.                                                                                                                                     │
│ get         Retrieves a specific function using its id or label.                                                                                                                                   │
│ init        Create a new local function. If the `--remote-id` option is used, the corresponding function will be pulled from the remote server instead.                                            │
│ list        Lists all available functions.                                                                                                                                                         │
│ pull        Retrieve and update your local function code with the latest changes from the remote server.                                                                                           │
│ push        Update and synchronize your local function code with the remote server.                                                                                                                │
│ restart     Restart the function.                                                                                                                                                                  │
│ status      Check the status of the functions.                                                                                                                                                     │
│ stop        Stop the function.                                                                                                                                                                     │
│ update      Update a function.                                                                                                                                                                     │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

```

## CRUD over UbiFunctions

### Create a function
Create an UbiFunction on your Ubidots account.

```bash
                                                                                                                                                                                                      
 Usage: ubidots functions add [OPTIONS] NAME                                                                                                                                                          
                                                                                                                                                                                                      
╭─ Arguments ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    name      TEXT  The name of the function. [required]                                                                                                                                          │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --profile                     TEXT                                                                              Profile to use to interact with the remote server.                                 │
│ --label                       TEXT                                                                              The label for the function.                                                        │
│ --timeout                     INTEGER                                                                           Timeout for the function in seconds. [default: 10]                                 │
│ --runtime                     [python3.9:lite|python3.9:base|python3.9:full|python3.11:lite|python3.11:base|py  The runtime for the function. [default: nodejs20.x:lite]                           │
│                               thon3.11:full|nodejs20.x:lite|nodejs20.x:base]                                                                                                                       │
│ --raw            --no-raw                                                                                       Flag to determine if the output should be in raw format. [default: no-raw]         │
│ --methods                     [GET|POST]                                                                        The HTTP methods the function will respond to. [default: GET]                      │
│ --cors           --no-cors                                                                                      Flag to enable Cross-Origin Resource Sharing (CORS) for the function.              │
│                                                                                                                 [default: no-cors]                                                                 │
│ --environment                 TEXT                                                                              environment in JSON format. [default: []]                                          │
│ --help                                                                                                          Show this message and exit.                                                        │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### Get an UbiFunction
Retrieve an UbiFunction from Ubidots.
```bash
 Usage: ubidots functions get [OPTIONS]                                                                                                                                                               
╭─ Options ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --profile                    TEXT          Profile to use to interact with the remote server.                                                                                                      │
│ --id                         TEXT          Unique **identifier** for the function. If both id and label are provided, the id takes precedence.                                                     │
│ --label                      TEXT          Descriptive label **identifier** for the function. Ignored if id is provided.                                                                           │
│ --fields                     TEXT          Comma-separated fields to process * e.g. field1,field2,field3. * Available fields: (url, id, label, name, isActive, createdAt, serverless, triggers,    │
│                                            environment, zipFileProperties).                                                                                                                        │
│                                            [default: id,label,name]                                                                                                                                │
│ --format                     [table|json]  [default: table]                                                                                                                                        │
│ --verbose    --no-verbose                  [default: no-verbose]                                                                                                                                   │
│ --help                                     Show this message and exit.                                                                                                                             │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### Update an UbiFunction
Update an existing UbiFunction in Ubidots
```bash
                                                                                                                                             
 Usage: ubidots functions update [OPTIONS]                                                                                                   
                                                                                                                                             
╭─ Options ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --id                          TEXT                                                  Unique **identifier** for the function. If both id    │
│                                                                                     and label are provided, the id takes precedence.      │
│ --label                       TEXT                                                  Descriptive label **identifier** for the function.    │
│                                                                                     Ignored if id is provided.                            │
│ --new-label                   TEXT                                                  The label for the device.                             │
│ --new-name                    TEXT                                                  The name of the device.                               │
│ --runtime                     [python3.9:lite|python3.9:base|python3.9:full|python  The runtime for the function. [default: None]         │
│                               3.11:lite|python3.11:base|python3.11:full|nodejs20.x                                                        │
│                               :lite|nodejs20.x:base]                                                                                      │
│ --raw            --no-raw                                                           Flag to determine if the output should be in raw      │
│                                                                                     format.                                               │
│                                                                                     [default: no-raw]                                     │
│ --cors           --no-cors                                                          Flag to enable Cross-Origin Resource Sharing (CORS)   │
│                                                                                     for the function.                                     │
│                                                                                     [default: no-cors]                                    │
│ --cron                        TEXT                                                  Cron expression to schedule the function for periodic │
│                                                                                     execution.                                            │
│                                                                                     [default: None]                                       │
│ --timeout                     INTEGER                                               Timeout for the function in seconds. [default: None]  │
│ --environment                 TEXT                                                  environment in JSON format. [default: []]             │
│ --profile                     TEXT                                                  Profile to use to interact with the remote server.    │
│ --methods                     [GET|POST]                                            The HTTP methods the function will respond to.        │
│                                                                                     [default: None]                                       │
│ --help                                                                              Show this message and exit.                           │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

```

### Delete an UbiFunction
Delete an UbiFunction from your Ubidots account.

```bash
                                                                                                                                                                                                    
 Usage: ubidots functions delete [OPTIONS]                                                                                                                                                          
                                                                                                                                                                                                    
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --profile                      TEXT  Profile to use to interact with the remote server.                                                                                                          │
│ --id                           TEXT  Unique **identifier** for the function. If both id and label are provided, the id takes precedence.                                                         │
│ --label                        TEXT  Descriptive label **identifier** for the function. Ignored if id is provided.                                                                               │
│ --yes      -y                        Confirm file overwrite without prompt.                                                                                                                      │
│ --verbose      --no-verbose          [default: no-verbose]                                                                                                                                       │
│ --help                               Show this message and exit.                                                                                                                                 │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

**Note**: This command permanently deletes the UbiFunction, just like removing it through the platform, thus special care is advised. 


## Local development environment for UbiFunctions
Setting up a local development environment for UbiFunctions involves two steps:
1. Creating the local UbiFunction.
2. Starting the environment.

[Docker](https://docs.docker.com/engine/install/) is required for UbiFunctions local developing. Install it before proceeding further.

### Create a local UbiFunction

Creates a local function with the specified settings. If `--remote-id` is provided, all other options are ignored, and the function is pulled from the remote server with its existing configuration.
```bash
                                                                                                             
 Usage: ubidots functions init [OPTIONS]                                                                      
                                                                                                              
 Create a new local function. If the `--remote-id` option is used, the corresponding function will be pulled  
 from the remote server instead.                                                                              
                                                                                                              
╭─ Options ──────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --name                        TEXT                                  The name for the function.             │
│                                                                     [default: my_function]                 │
│ --language                    [python|nodejs]                       The programming language for the       │
│                                                                     function.                              │
│                                                                     [default: nodejs]                      │
│ --remote-id                   TEXT                                  The remote function ID.                │
│ --runtime                     [python3.9:lite|python3.9:base|pytho  The runtime for the function.          │
│                               n3.9:full|python3.11:lite|python3.11  [default: nodejs20.x:lite]             │
│                               :base|python3.11:full|nodejs20.x:lit                                         │
│                               e|nodejs20.x:base]                                                           │
│ --cors           --no-cors                                          Flag to enable Cross-Origin Resource   │
│                                                                     Sharing (CORS) for the function.       │
│                                                                     [default: no-cors]                     │
│ --methods                     [GET|POST]                            The HTTP methods the function will     │
│                                                                     respond to.                            │
│                                                                     [default: GET]                         │
│ --raw            --no-raw                                           Flag to determine if the output should │
│                                                                     be in raw format.                      │
│                                                                     [default: no-raw]                      │
│ --token                       TEXT                                  Token used to invoke the function.     │
│ --profile                     TEXT                                  Profile to use.                        │
│ --verbose    -v                                                     Enable verbose output.                 │
│ --help                                                              Show this message and exit.            │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### Start the local development environment
Start the local development environment in order to enable the UbiFunction execution. **Must be run inside an existing UbiFunction directory**. 

```bash
 Usage: ubidots functions start [OPTIONS]                                                                                                                                                      
                                                                                                                                                                                               
 Start Function.                                                                                                                                                                               
                                                                                                                                                                                               
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --verbose  -v        Enable verbose output.                                                                                                                                                 │
│ --help               Show this message and exit.                                                                                                                                            │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

This will ouput the following:
```bash

------------------
Starting Function:
------------------
Name: my_function
Local label: my_function
Runtime: nodejs20.x:lite
#
-------
INPUTS:
-------
Raw: False
Methods: GET
Token: 
    
URL: http://127.0.0.1:8042/my_function

> [DONE]: Function started successfully.

```

You can use the given URL to perform HTTP request and execute your local UbiFunction.


### Stop a function
Stops the running function.**Must be run inside an existing UbiFunction directory**.

```bash
Usage: ubidots functions stop [OPTIONS]

Stop the function.

╭─ Options ────────────────────────────────────────────────────────────╮
│ --verbose, -v   Enable verbose output.                               │
│ --help          Show this message and exit.                          │
╰─────────────────────────────────────────────────────────────────────╯
```

### Checking Function status

Displays the current status of the function.**Must be run inside an existing UbiFunction directory**.

```bash
Usage: ubidots functions status [OPTIONS]

Check the status of the function.

╭─ Options ────────────────────────────────────────────────────────────╮
│ --verbose, -v   Enable verbose output.                               │
│ --help          Show this message and exit.                          │
╰─────────────────────────────────────────────────────────────────────╯
```

### Restart a Function
Restarts the function.**Must be run inside an existing UbiFunction directory**.
```bash
Usage: ubidots functions restart [OPTIONS]

Restart the function.

╭─ Options ───────────────────────────────────────────────────────────╮
│ --verbose, -v   Enable verbose output.                               │
│ --help          Show this message and exit.                          │
╰─────────────────────────────────────────────────────────────────────╯
```

### Push Changes to Remote
Uploads and synchronizes local function code with the remote server. **Must be run inside an existing UbiFunction directory**.

```bash
Usage: ubidots functions push [OPTIONS]

Update and synchronize your local function code with the remote server.

╭─ Option ────────────────────────────────────────────────────────────╮
│ --yes, -y       Confirm overwrite without prompt.                    │
│ --profile, -p   Profile to use.                                       │
│ --verbose, -v   Enable verbose output.                               │
│ --help          Show this message and exit.                          │
╰─────────────────────────────────────────────────────────────────────╯
```

### Pull Latest Changes from Remote
Fetches the latest version of the function from the remote server. **Must be run inside an existing UbiFunction directory**.

```
Usage: ubidots functions pull [OPTIONS]

Retrieve and update your local function code with the latest changes from the remote server.

╭─ Options ───────────────────────────────────────────────────────────╮
│ --remote-id, -i  TEXT   Remote function ID.                          │
│ --profile, -p    TEXT   Profile to use.                              │
│ --yes, -y              Confirm overwrite without prompt.             │
│ --verbose, -v          Enable verbose output.                        │
│ --help                 Show this message and exit.                   │
╰─────────────────────────────────────────────────────────────────────╯
```

### List Remote Functions
Displays available functions on the remote server.

```bash
Usage: ubidots functions list [OPTIONS]

╭─Option────────────────────────────────────────────────────────────────────────────────╮
│ --profile          TEXT          Profile for remote interaction.                                   │
│ --fields           TEXT          Fields to display (e.g., `id,label,name`). 
|                                  [default: id,label]   
│
│ --filter           TEXT          Filter results by attributes.                                    │
│ --sort-by          TEXT          Sort results by a specific attribute.                           │
│ --page-size        INTEGER       Number of items per page.                                       │
│ --page             INTEGER       Page number to retrieve.                                        │
│ --format           [table|json]  Output format. [default: table]                              │
│ --help                           Show this message and exit.                                       │
╰──────────────────────────────────────────────────

```

### View Function Logs
Retrieves logs for a function. Must be run inside an existing UbiFunction directory unless `--remote` is passed.

```bash
Usage: ubidots functions logs [OPTIONS]

Get logs from the function.

╭─ Options ─────────────────────────────────────────────────────────╮
│ --tail, -n   TEXT   Show last N lines of logs. [default: all]        │
│ --follow, -f        Stream logs in real time.                        │
│ --profile, -p TEXT  Profile to use.                                  │
│ --remote, -r        Fetch logs from the remote server.               │
│ --verbose, -v       Enable verbose output.                           │
│ --help              Show this message and exit.                      │
╰─────────────────────────────────────────────────────────────────────╯
```