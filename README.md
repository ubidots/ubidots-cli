# Ubidots CLI 
1. [Overview](#overview)
2. [Requirements](#requirements)
3. [Installation](#installation)
4. [Available commands](#available-commands)
5. [`ubidots config`](#ubidots-config)
6. [`ubidots devices`](#ubidots-devices)
7. [`ubidots variables`](#ubidots-variables)

# Overview 
The Ubidots command line interface (CLI) provides:
1. A fully-featured local development environment for UbiFunctions, replicating runtimes and their included libraries, enabling developers to seamlessly write, test, and deploy serverless functions directly from their local machine.
2. CRUD (Create, Read, Update, Delete) operations for the following entities in Ubidots:
   - Devices
   - Variables
   - Functions

# Requirements

- [Python 3.9 or higher](https://www.python.org/)
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
This command's subcommands allows CRUD operations over devices on Ubidots.
```bash
Usage: ubidots devices [OPTIONS] COMMAND [ARGS]...                                                                             
                                                                                                                                
 Device management and operations.                                                                                              
                                                                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                  │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ add             Adds a new device.                                                                                           │
│ delete          Deletes a specific device using its id or label.                                                             │
│ get             Retrieves a specific device using its id or label.                                                           │
│ list            Lists all available devices.                                                                                 │
│ update          Update a device.                                                                                             │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```
## Create a device
`ubidots devices add` creates a new device on Ubidots.
```bash
Usage: ubidots devices add [OPTIONS] LABEL                                                                                                                                                        
                                                                                                                                                                                                   
╭─ Arguments ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    label      TEXT  The label for the device. [required]                                                                                                                                      │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --name                TEXT  The name of the device.                                                                                                                                             │
│ --description         TEXT  A brief description of the device.                                                                                                                                  │
│ --organization        TEXT  The organization associated with the device. Its id or ['~label' | \~label].                                                                                        │
│ --tags                TEXT  Comma-separated tags for the device. e.g. tag1,tag2,tag3                                                                                                            │
│ --properties          TEXT  Device properties in JSON format. [default: {}]                                                                                                                     │
│ --help                      Show this message and exit.                                                                                                                                         │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

## Get a device
`ubidots devices get` retrieves a device from Ubidots.
```bash
Usage: ubidots devices get [OPTIONS]                                                                                                                                                        
                                                                                                                                                                                             
╭─ Options ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --id            TEXT  Unique **identifier** for the device. If both id and label are provided, the id takes precedence.                                                                   │
│ --label         TEXT  Descriptive label **identifier** for the device. Ignored if id is provided.                                                                                         │
│ --fields        TEXT  Comma-separated fields to process. e.g. field1,field2,field3 [default: id,label,name]                                                                               │
│ --help                Show this message and exit.                                                                                                                                         │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```


## Update a device
`ubidots devices update` updates an existing device's settings on Ubidots. 

```bash
 Usage: ubidots devices update [OPTIONS]                                                                                                                                                     
                                                                                                                                                                                             
╭─ Options ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --id                  TEXT  Unique **identifier** for the device. If both id and label are provided, the id takes precedence.                                                             │
│ --label               TEXT  Descriptive label **identifier** for the device. Ignored if id is provided.                                                                                   │
│ --new-label           TEXT  The label for the device.                                                                                                                                     │
│ --new-name            TEXT  The name of the device.                                                                                                                                       │
│ --description         TEXT  A brief description of the device.                                                                                                                            │
│ --organization        TEXT  The organization associated with the device. Its id or ['~label' | \~label].                                                                                  │
│ --tags                TEXT  Comma-separated tags for the device. e.g. tag1,tag2,tag3                                                                                                      │
│ --properties          TEXT  Device properties in JSON format. [default: {}]                                                                                                               │
│ --help                      Show this message and exit.                                                                                                                                   │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```


## Delete a device
`ubidots devices delete` deletes a device from your Ubidots account.

```bash
Usage: ubidots devices delete [OPTIONS]                                                                                                                                                     
                                                                                                                                                                                             
╭─ Options ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --id           TEXT  Unique **identifier** for the device. If both id and label are provided, the id takes precedence.                                                                    │
│ --label        TEXT  Descriptive label **identifier** for the device. Ignored if id is provided.                                                                                          │
│ --help               Show this message and exit.                                                                                                                                          │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```
**Note**: This command permanently deletes the device, just like removing it through the platform, thus special care is advised. 


# `ubidots variables`
This command's subcommands allow CRUD operations over variables on Ubidots. 

## Create variable
`ubidots variables add` creates a new 

