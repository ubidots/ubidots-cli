# Changelog

## [Unreleased]

### ✨ New Features

- Added Python 3.13 and 3.14 support (version constraint expanded from `<3.13` to `<3.15`)
- Upgraded `typer` from `^0.12.0` to `^0.15.0` for compatibility with click 8.3.x on newer Python versions
- Added `py313` to tox test matrix

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
