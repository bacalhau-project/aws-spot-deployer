# Spot Deployer - Modular Architecture

This is the modularized version of the AWS Spot Instance Deployer, broken down into manageable components that stay within Claude's token limits.

## Directory Structure

```
spot_deployer/
├── __init__.py
├── main.py                 # Main entry point
├── commands/              # Command implementations (verbs)
│   ├── __init__.py
│   ├── create.py          # Create instances (~500 lines)
│   ├── destroy.py         # Destroy instances (~300 lines)
│   ├── list.py            # List instances (~40 lines)
│   ├── setup.py           # Setup configuration (~40 lines)
│   └── help.py            # Show help (~25 lines)
├── core/                  # Core business logic
│   ├── __init__.py
│   ├── config.py          # Configuration management (~130 lines)
│   ├── state.py           # State management (~45 lines)
│   ├── constants.py       # Constants and config values (~40 lines)
│   └── instance_manager.py # Instance creation logic (~250 lines)
└── utils/                 # Utility functions
    ├── __init__.py
    ├── display.py         # Rich terminal output (~70 lines)
    ├── aws.py             # AWS utilities (~180 lines)
    ├── logging.py         # Logging utilities (~90 lines)
    ├── ssh.py             # SSH and file transfer (~220 lines)
    └── cloud_init.py      # Cloud-init generation (~350 lines)
```

## Module Sizes

Each module is designed to be small enough for Claude to process comfortably:

- **Commands**: 25-500 lines each
  - `create.py`: The largest command at ~500 lines
  - `destroy.py`: Enhanced UI version at ~300 lines
  - Others: Under 50 lines each

- **Core**: 40-250 lines each
  - `instance_manager.py`: Instance creation logic extracted from create command
  - `config.py`: Configuration management
  - `state.py`: Simple JSON state management
  - `constants.py`: Shared constants

- **Utils**: 70-350 lines each
  - `cloud_init.py`: The largest utility at ~350 lines
  - `ssh.py`: SSH operations at ~220 lines
  - `aws.py`: AWS-specific utilities at ~180 lines
  - Others: Under 100 lines each

## Usage

The modular version can be used exactly like the original:

```bash
# Use the new modular script
./deploy_spot_modular.py help
./deploy_spot_modular.py setup
./deploy_spot_modular.py create
./deploy_spot_modular.py list
./deploy_spot_modular.py destroy

# Or import and use programmatically
from spot_deployer.main import main
main()
```

## Benefits of Modularization

1. **Token Limit Friendly**: Each file is small enough for Claude to process without hitting token limits
2. **Better Organization**: Related functionality is grouped together
3. **Easier Testing**: Individual components can be tested in isolation
4. **Clearer Dependencies**: Import statements show exactly what each module depends on
5. **Focused Work**: You can work on specific features without loading the entire codebase

## Working with Modules

When asking Claude to work on specific functionality:

1. **For command changes**: Point to the specific command file (e.g., `commands/create.py`)
2. **For AWS operations**: Look at `utils/aws.py` or `core/instance_manager.py`
3. **For UI/display changes**: Check `utils/display.py` and the command files
4. **For configuration**: See `core/config.py`
5. **For state management**: See `core/state.py`

This modular structure makes it easy to understand and modify specific parts of the system without needing to load the entire 2800+ line file.