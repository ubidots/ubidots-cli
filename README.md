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
- [Python 3.12.2 or higher](https://www.python.org/)
- [Docker](https://docs.docker.com/engine/install/ubuntu/) (required only for local UbiFunctions development)


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

# `ubidots config`
This command configures the CLI cloud settings required to connect with your Ubidots account. This means that you must run this command prior to any other. 


It will prompt you for:

- **API domain**: Leave the default value unless you are on a Ubidots private deployment.
- **Authentication method**: The authentication method that you'd like to use.
- **Access token**: A valid [Ubidots token](https://help.ubidots.com/en/articles/590078-find-your-token-from-your-ubidots-account)

```bash
ubidots config

API Domain [https://industrial.api.ubidots.com]: 
Authentication Method [TOKEN]: 
Access Token [*******************************pPem]: 

> [DONE]: Configuration saved successfully.
```

This configuration will be saved at `$HOME/.ubidots_cli/config.yaml`. You can check it by running `cat`:

```bash
cat $HOME/.ubidots_cli/config.yaml

access_token: <ubidots-token> 
api_domain: https://industrial.api.ubidots.com
auth_method: X-Auth-Token
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
│ --help                                         Show this message and exit.   │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## Get a variable
Retrieve a variable from Ubidots.

```bash
 Usage: ubidots variables get [OPTIONS]                                         
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│    --id            TEXT  Unique identifier for the variable. [required]      │
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
│    --help              Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

**Note**: This command permanently deletes the variable, just like removing it through the platform, thus special care is advised. 


# `ubidots functions`
This command allows to:
- Perform CRUD operations over variables in Ubidots.
- Set up a local development environment featuring all the runtimes supported on UbiFunctions and their respective libraries. Docker is required for this.

```bash
 Usage: ubidots functions [OPTIONS] COMMAND [ARGS]...                          
                                                                               
 Tool for managing and deploying functions.                                    
                                                                               
╭─ Options ───────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                 │
╰─────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ──────────────────────────────────────────────────────────────────╮
│ add       Adds a new function.                                              │
│ delete    Deletes a specific function using its id or label.                │
│ get       Retrieves a specific function using its id or label.              │
│ list      Lists all available functions.                                    │
│ update    Update a function.                                                │
╰─────────────────────────────────────────────────────────────────────────────╯
```

## CRUD over UbiFunctions

### Create a function
Create an UbiFunction on your Ubidots account.

```bash
 Usage: ubidots functions add [OPTIONS] NAME                                   
                                                                               
╭─ Arguments ─────────────────────────────────────────────────────────────────╮
│     name      TEXT  The name of the function. [required]                    │
╰─────────────────────────────────────────────────────────────────────────────╯
╭─ Options ───────────────────────────────────────────────────────────────────╮
│ --label                       TEXT                   The label for the      │
│                                                      function.              │
│ --runtime                     [python3.9:lite|pytho  The runtime for the    │
│                               n3.9:base|python3.9:f  function.              │
│                               ull|python3.11:lite|p  [default:              │
│                               ython3.11:base|python  nodejs20.x:lite]       │
│                               3.11:full|nodejs20.x:                         │
│                               lite|nodejs20.x:base]                         │
│ --raw            --no-raw                            Flag to determine if   │
│                                                      the output should be   │
│                                                      in raw format.         │
│                                                      [default: no-raw]      │
│ --token                       TEXT                   Optional               │
│                                                      authentication token   │
│                                                      to invoke the          │
│                                                      function.              │
│ --methods                     TEXT                   The HTTP methods the   │
│                                                      function will respond  │
│                                                      to.                    │
│                                                      [default: GET]         │
│ --cors           --no-cors                           Flag to enable         │
│                                                      Cross-Origin Resource  │
│                                                      Sharing (CORS) for the │
│                                                      function.              │
│                                                      [default: no-cors]     │
│ --cron                        TEXT                   Cron expression to     │
│                                                      schedule the function  │
│                                                      for periodic           │
│                                                      execution.             │
│                                                      [default: * * * * *]   │
│ --environment                 TEXT                   environment in JSON    │
│                                                      format.                │
│                                                      [default: []]          │
│ --help                                               Show this message and  │
│                                                      exit.                  │
╰─────────────────────────────────────────────────────────────────────────────╯
```

### Get an UbiFunction
Retrieve an UbiFunction from Ubidots.
```bash
 Usage: ubidots functions get [OPTIONS]                                        
                                                                               
╭─ Options ───────────────────────────────────────────────────────────────────╮
│ --id            TEXT  Unique identifier for the function. If both id        │                       and label are provided, the id takes precedence.      │
│ --label         TEXT  Descriptive label identifier for the function.       
│                       Ignored if id is provided.                            │
│ --fields        TEXT  Comma-separated fields to process. e.g.               │
│                       field1,field2,field3                                  │
│                       [default: id,label,name]                              │
│ --help                Show this message and exit.                           │
╰─────────────────────────────────────────────────────────────────────────────╯
```

### Update an UbiFunction
Update an existing UbiFunction in Ubidots
```bash
 Usage: ubidots functions update [OPTIONS]                                                     
                                                                                               
╭─ Options ───────────────────────────────────────────────────────────────────────────────────╮
│ --id                          TEXT                           Unique identifier for the      │
│                                                              function. If both id and label │                                                              are provided, the id takes     │
│                                                              precedence.                    │
│ --label                       TEXT                           Descriptive label              │
│                                                              identifier for the             │
│                                                              function. Ignored if id is    
│                                                              provided.                      │
│ --new-label                   TEXT                           The label for the device.      │
│ --new-name                    TEXT                           The name of the device.        │
│ --runtime                     [python3.9:lite|python3.9:bas  The runtime for the function.  │
│                               e|python3.9:full|python3.11:l  [default: nodejs20.x:lite]     │
│                               ite|python3.11:base|python3.1                                 │
│                               1:full|nodejs20.x:lite|nodejs                                 │
│                               20.x:base]                                                    │
│ --raw            --no-raw                                    Flag to determine if the       │
│                                                              output should be in raw        │
│                                                              format.                        │
│                                                              [default: no-raw]              │
│ --token                       TEXT                           Optional authentication token  │
│                                                              to invoke the function.        │
│ --methods                     TEXT                           The HTTP methods the function  │
│                                                              will respond to.               │
│                                                              [default: GET]                 │
│ --cors           --no-cors                                   Flag to enable Cross-Origin    │
│                                                              Resource Sharing (CORS) for    │
│                                                              the function.                  │
│                                                              [default: no-cors]             │
│ --cron                        TEXT                           Cron expression to schedule    │
│                                                              the function for periodic      │
│                                                              execution.                     │
│                                                              [default: * * * * *]           │
│ --environment                 TEXT                           environment in JSON format.    │
│                                                              [default: []]                  │
│ --help                                                       Show this message and exit.    │
╰─────────────────────────────────────────────────────────────────────────────────────────────╯
```

### Delete an UbiFunction
Delete an UbiFunction from your Ubidots account.

```bash
 Usage: ubidots functions delete [OPTIONS]                                                     
                                                                                               
╭─ Options ───────────────────────────────────────────────────────────────────────────────────╮
│ --id           TEXT  Unique identifier for the function. If both id and label are          
│                      provided, the id takes precedence.                                     │
│ --label        TEXT  Descriptive label **identifier** for the function. Ignored if id is    │
│                      provided.                                                              │
│ --help               Show this message and exit.                                            │
╰─────────────────────────────────────────────────────────────────────────────────────────────╯
```

**Note**: This command permanently deletes the UbiFunction, just like removing it through the platform, thus special care is advised. 


## Local development environment for UbiFunctions
Setting up a local development environment for UbiFunctions involves two steps:
1. Creating the local UbiFunction.
2. Starting the environment.

[Docker](https://docs.docker.com/engine/install/) is required for UbiFunctions local developing. Install it before proceeding further.

### Create a local UbiFunction
Create a new local UbiFunction with the given runtime, method and other settings. 
```bash
 Usage: ubidots functions new [OPTIONS]                                                                                    
                                                                                                                           
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --name                          TEXT                                        The name of the project folder.             │
│                                                                             [default: my_function]                      │
│ --runtime                       [python3.9:lite|python3.9:base|python3.9:f  The runtime for the function.               │
│                                 ull|python3.11:lite|python3.11:base|python  [default: nodejs20.x:lite]                  │
│                                 3.11:full|nodejs20.x:lite|nodejs20.x:base]                                              │
│ --cors             --no-cors                                                Flag to enable Cross-Origin Resource        │
│                                                                             Sharing (CORS) for the function.            │
│                                                                             [default: no-cors]                          │
│ --cron                          TEXT                                        Cron expression to schedule the function    │
│                                                                             for periodic execution.                     │
│                                                                             [default: * * * * *]                        │
│ --methods                       TEXT                                        The HTTP methods the function will respond  │
│                                                                             to.                                         │
│                                                                             [default: GET]                              │
│ --raw              --no-raw                                                 Flag to determine if the output should be   │
│                                                                             in raw format.                              │
│                                                                             [default: no-raw]                           │
│ --interactive  -i                                                           Enable interactive mode to select options   │
│                                                                             through prompts.                            │
│ --verbose      -v                                                           Enable verbose output.                      │
│ --help                                                                      Show this message and exit.                 │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### Start the local development environment
Start the local development environment in order to enable the UbiFunction execution. 
```bash
 Usage: ubidots functions start [OPTIONS]                                                                                  
                                                                                                                           
 Initialize the function container environment for execution.                                                              
                                                                                                                           
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --cors         --no-cors             Flag to enable Cross-Origin Resource Sharing (CORS) for the function.              │
│                                      [default: no-cors]                                                                 │
│ --cron                      TEXT     Cron expression to schedule the function for periodic execution.                   │
│                                      [default: * * * * *]                                                               │
│ --methods                   TEXT     The HTTP methods the function will respond to. [default: GET]                      │
│ --raw          --no-raw              Flag to determine if the output should be in raw format. [default: no-raw]         │
│ --timeout                   INTEGER  Maximum time (in seconds) the function is allowed to run before being terminated.  │
│                                      [max: 300]                                                                         │
│                                      [default: 10]                                                                      │
│ --token                     TEXT     Optional authentication token to invoke the function.                              │
│ --verbose  -v                        Enable verbose output.                                                             │
│ --help                               Show this message and exit.                                                        │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

This will ouput the following:
```bash

    ------------------
    Starting Function:
    ------------------
    Name: prueba-python-push
    Runtime: python3.9:base
    Local label: lambda_fn_prueba-python-push_Bk2L4H5bKp

    -------
    INPUTS:
    -------
    Raw: False
    Methods: GET
    Token: 
        
http://172.18.0.2:8042/lambda_fn_prueba-python-push_Bk2L4H5bKp

> [DONE]: Function started successfully.
```

You can use the given URL to perform HTTP request and execute your local UbiFunction.