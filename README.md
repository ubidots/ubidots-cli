# Ubidots CLI

**Ubidots CLI** is a command-line interface for interacting with Ubidots services. It simplifies the management of your IoT devices and data.

## Supported Python Versions

This CLI requires **Python 3.9** or higher.

## Installation

To install the Ubidots CLI, run the following command:

```bash
$ pip install ubidots-cli
```

## Usage

After installation, you can use the ubidots command. To see the available commands, run:

```bash
$ ubidots --help

                                                                                
 Usage: ubidots [OPTIONS] COMMAND [ARGS]...                                     
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --install-completion        [bash|zsh|fish|powershe  Install completion for  │
│                             ll|pwsh]                 the specified shell.    │
│                                                      [default: None]         │
│ --show-completion           [bash|zsh|fish|powershe  Show completion for the │
│                             ll|pwsh]                 specified shell, to     │
│                                                      copy it or customize    │
│                                                      the installation.       │
│                                                      [default: None]         │
│ --help                                               Show this message and   │
│                                                      exit.                   │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ config          Configure general settings for the CLI.                      │
│ devices         Device management and operations.                            │
│ functions       Tool for managing and deploying functions.                   │
│ variables       Variable management and operations.                          │
| ...                                                                          |
╰──────────────────────────────────────────────────────────────────────────────╯

```


### Configuring Credentials
To configure credentials, run:
```bash
$ ubidots config

API Domain [https://industrial.api.ubidots.com]: 
Authentication Method [TOKEN]: 
Access Token [*******************************pPem]: 

> [DONE]: Configuration saved successfully.


```


You can check the configuration file at ```.ubidots_cli/config.yaml```:
```bash
$ cat .ubidots_cli/config.yaml

access_token: <your-token>
api_domain: https://industrial.api.ubidots.com
auth_method: X-Auth-Token
```