# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A **modern AWS spot instance deployment tool** for deploying Bacalhau compute nodes and sensor simulations. Features a clean Python package structure with beautiful Rich terminal output.

## Key Architecture

- **Package structure**: Modular design in `spot_deployer/` package
- **State management**: JSON-based (`instances.json`) for simplicity
- **Configuration**: YAML-based (`config.yaml`) with sensible defaults
- **Caching**: File-based AMI caching (`.aws_cache/`)
- **UI**: Rich library for beautiful terminal tables and live progress
- **Docker-first**: Distributed as Docker container via `spot-dev` script
- **Node Identity**: Deterministic sensor identity generation for Bacalhau integration

## Deployment Philosophy

**CRITICAL**: This project uses immutable infrastructure. ALWAYS destroy and recreate instances when testing changes. Never patch running instances.

### Standard Development Workflow
```bash
# 1. Make changes to deployment code
# 2. Destroy ALL existing instances
./spot-dev destroy

# 3. Verify cleanup
./spot-dev list  # Should be empty

# 4. Deploy fresh instances
./spot-dev create

# 5. Check deployment status
./spot-dev list
```

## Development Commands

### Basic Usage
```bash
# Setup configuration
./spot-dev setup

# Deploy instances (hands-off approach)
./spot-dev create
# Note: After creation, instances configure themselves autonomously
# Check back in ~5 minutes for fully configured instances

# List running instances
./spot-dev list

# Destroy all instances
./spot-dev destroy

# Get help
./spot-dev help
```


### Advanced VPC Cleanup
```bash
# Scan VPCs (dry run)
uv run delete_vpcs.py --dry-run

# Full cleanup
uv run delete_vpcs.py
```


### Code Quality
```bash
# Linting - ALWAYS run before committing
uv run ruff check spot_deployer/

# Auto-fix linting issues where possible
uv run ruff check spot_deployer/ --fix

# Format code
uv run ruff format spot_deployer/
```

**Important:** Always run `uv run ruff check spot_deployer/` to verify syntax and code quality before committing changes.

## Core Components

### Main Entry Points
- `spot_deployer/` - Main package directory
- `spot-dev` - Docker-based CLI wrapper
- `delete_vpcs.py` - Advanced VPC cleanup utility

### Key Classes
- `SimpleConfig` - YAML configuration management
- `SimpleStateManager` - JSON-based instance state tracking
- `NodeIdentityGenerator` - Deterministic sensor identity creation

### File Layout
```
├── spot_deployer/              # Main package
│   ├── commands/               # CLI commands (create, destroy, list, etc.)
│   ├── core/                   # Core classes (config, state, constants)
│   └── utils/                  # Utilities (AWS, SSH, display, etc.)
├── instance/
│   ├── scripts/                # Scripts deployed to instances
│   └── config/                 # Configuration templates
├── spot-dev                    # Docker CLI wrapper
├── delete_vpcs.py              # VPC cleanup utility
├── config.yaml                 # Runtime configuration
├── config.yaml.example         # Comprehensive example
├── instances.json              # Runtime state (auto-created)
├── .aws_cache/                 # AMI cache directory
└── files/                      # User files to upload
```

## Configuration Structure

### config.yaml
```yaml
aws:
  total_instances: 3
  username: ubuntu
  ssh_key_name: my-key
  files_directory: "files"
  scripts_directory: "instance/scripts"
regions:
  - us-west-2:
      machine_type: t3.medium
      image: auto  # Auto-discovers latest Ubuntu 22.04
```

### Bacalhau Orchestrator Configuration

**IMPORTANT**: Bacalhau compute nodes require orchestrator connection details. These are provided via credential files:

#### Credential Files (Required)

Create these files in the `files/` directory before deployment:

1. **`files/orchestrator_endpoint`** - Contains the NATS endpoint URL
   ```
   nats://orchestrator.example.com:4222
   ```

2. **`files/orchestrator_token`** - Contains the authentication token
   ```
   your-secret-token-here
   ```

**Security Notes:**
- The files are listed in `.gitignore` to prevent accidental commits
- If these files are missing, compute nodes will start but won't connect to any orchestrator

#### How It Works

1. During `deploy_spot.py create`, the credential files are uploaded to `/opt/uploaded_files/`
2. The `bacalhau.service` runs `generate_bacalhau_config.sh` which:
   - Reads the credential files
   - Generates a complete `/bacalhau_node/config.yaml` with orchestrator endpoint and token injected
3. Docker Compose mounts the generated config.yaml directly into the container
   - No environment variables needed - all configuration is in the YAML file

## Key Design Patterns

### Immutable Infrastructure
- **NEVER** modify running instances
- **ALWAYS** destroy and recreate for any changes
- Treat instances as disposable cattle, not pets
- Fix issues in code, not on instances

### Hands-Off Deployment
- Upload files and enable services, then disconnect
- No long-running SSH connections during setup
- Cloud-init handles package installation only
- deploy_services.py handles all application setup
- SystemD services start automatically after reboot

### Simple State Management
- JSON file for instance tracking
- Region-based cleanup
- Automatic state synchronization

### Rich UI Integration
- Beautiful tables for instance lists
- Progress bars for file upload only
- Styled success/error messages (✅ ❌ ℹ️ ⚠️)
- Minimal status updates (hands-off approach)

### AWS Integration
- Direct boto3 calls (no abstraction layers)
- AMI auto-discovery with caching
- VPC/subnet auto-discovery
- Spot instance lifecycle management

### Error Handling
- Graceful degradation when regions fail
- Clear error messages with guidance
- Automatic cleanup on failure
- Retry logic for transient issues

### Node Identity System
- Deterministic generation based on EC2 instance ID
- Realistic US city locations with GPS coordinates
- Authentic sensor manufacturer/model data
- Automatic generation during startup
- Output to `/opt/sensor/config/node_identity.json`

## Development Notes

### Performance Characteristics
- **Startup time**: ~0.15 seconds (93% faster than original)
- **File size**: 30KB (65% reduction from original)
- **Dependencies**: 3 packages only (boto3, pyyaml, rich)

### Code Style
- Full type annotations throughout
- Clear docstrings for all functions
- Consistent error handling patterns
- Single-file design for simplicity


## Common Development Tasks

### Adding New Features
1. Follow modular package structure
2. Update configuration schema if needed
3. Test with real AWS resources using `./spot-dev`

### Debugging
- **IMPORTANT**: Never debug by patching instances
- Fix issues in source code
- Destroy all instances: `./spot-dev destroy`
- Deploy fresh: `./spot-dev create`
- Check `instances.json` for state issues
- Use `--dry-run` with VPC cleanup for safety
- Verify deployment log at `/opt/deployment.log` on instances

### Console Logging with Instance Context
The deployment tool includes a custom `ConsoleLogger` that enhances log output with instance identification and IP addresses. During deployment, all SUCCESS and ERROR messages are automatically prefixed with:
- Instance ID and IP address: `[i-1234567890abcdef0 @ 54.123.45.67] SUCCESS: Created`
- This helps identify which specific instance is producing each log message
- Makes it easy to SSH into the correct instance for debugging

Example output:
```
[i-0a1b2c3d4e5f67890 @ 52.34.56.78] SUCCESS: Created
[i-0a1b2c3d4e5f67890 @ 52.34.56.78] SUCCESS: Setup complete - rebooting to start services
[i-9f8e7d6c5b4a32109 @ 54.67.89.12] SUCCESS: Created
[i-9f8e7d6c5b4a32109 @ 54.67.89.12] ERROR: File upload failed
```

### Configuration Changes
- Always provide sensible defaults
- Update `config.yaml.example` for new options
- Maintain backward compatibility
- Test with minimal configuration

### Working with Node Identities
- Identities are deterministic based on instance ID
- Test with: `INSTANCE_ID=i-test python3 instance/scripts/generate_node_identity.py`
- Check generated identity: `cat /opt/sensor/config/node_identity.json | jq .`
- Add new cities/manufacturers in `generate_node_identity.py`
