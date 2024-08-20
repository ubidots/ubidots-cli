# Ubidots CLI
This is the main repository for **Ubidots CLI**, a command-line interface for interacting with Ubidots services. It simplifies the process of managing your IoT devices and data.

## Requirements
- **[Poetry](https://python-poetry.org/)** >=1.7.1 (Project started with version 1.7.1)
- **[Pyenv](https://github.com/pyenv/pyenv)** (For managing multiple Python versions)
- **[Python](https://www.python.org/)** >=3.12.2 (Project started with version 3.12.2)
- **[Docker](https://www.docker.com/)** (Currently required to execute functions)
- **[Argo](https://bitbucket.org/ubidots/argo/src/master/)** (Use the `master_v2` branch from the Argo repository, necessary for executing functions)

## Installation

To get started, clone the repository:
```bash
git clone git@bitbucket.org:ubidots/ubidots-cli.git
```

### Poetry Installation
Install Poetry using the official instructions found at [Poetry Installation Guide](https://python-poetry.org/docs/#installation).

### Python Version Management with `pyenv`
To manage multiple Python versions or ensure you're using the correct Python version for this project, `pyenv` is a recommended tool.

1. **Install `pyenv`**:
   Follow the official installation instructions found at [pyenv Installation Guide](https://github.com/pyenv/pyenv#installation).

2. **Install the required Python version**:
   Once `pyenv` is installed, you can install the specific Python version required for this project (as specified in the `.python-version` file):
   ```bash
   pyenv install 3.12.2
   ```

3. **Set the local Python version**:
   To use the installed Python version for this project, set it locally:
   ```bash
   pyenv local 3.12.2
   ```

   This ensures that whenever you are in the project directory, `pyenv` will use the specified Python version.


### Python Installation
To install the project dependencies, navigate to the project directory and run:
   ```bash
   poetry install
   ```

### Docker Installation
Docker is a platform for developing, shipping, and running applications. For detailed installation instructions, please visit the [Docker Official Website](https://docs.docker.com/get-docker/).

### Argo Installation
Clone the Argo repository and switch to the `master_v2` branch:
```bash
git clone git@bitbucket.org:ubidots/argo.git
```
Refer to the README.md file in the Argo repository for more installation details.

## Usage

Navigate to the `ubidots-cli` directory and activate the environment using:
```bash
poetry shell
```



Run `ubidots --help` to view available CLI commands. Each command may have its subcommands. Explore these in more detail using the `--help` flag.
```bash
> ubidots --help
                                                                                                                                              
 Usage: ubidots [OPTIONS] COMMAND [ARGS]...                                                                                                   
                                                                                                                                              
╭─ Options ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --install-completion        [bash|zsh|fish|powershell|pwsh]  Install completion for the specified shell. [default: None]                   │
│ --show-completion           [bash|zsh|fish|powershell|pwsh]  Show completion for the specified shell, to copy it or customize the          │
│                                                              installation.                                                                 │
│                                                              [default: None]                                                               │
│ --help                                                       Show this message and exit.                                                   │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ config            Configure general settings for the CLI.                                                                                  │
│ dev               Device management and operations.                                                                                        │
│ fn                Tool for managing and deploying functions via API.                                                                       │
│ var               Variable management and operations.                                                                                      │
| ...                                                                                                                                        |
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯


```

### Configuring Credentials
To configure credentials, run:
```bash
> ubidots config

API Domain [https://industrial.api.ubidots.com]: 
Authentication Method [TOKEN]: 
Access Token [*******************************kz4j]: 
Configuration saved successfully.
```
