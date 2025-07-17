# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A **simplified AWS spot instance deployment tool** focused on simplicity and maintainability. Originally a 2400+ line enterprise codebase, now condensed to ~820 lines in a single file (`deploy_spot.py`) with beautiful Rich terminal output.

## Key Architecture

- **Single-file design**: All functionality in `deploy_spot.py`
- **State management**: JSON-based (`instances.json`) rather than database
- **Configuration**: YAML-based (`config.yaml`) with sensible defaults
- **Caching**: Simple file-based AMI caching (`.aws_cache/`)
- **UI**: Rich library for beautiful terminal tables and progress
- **Node Identity**: Deterministic sensor identity generation for Bacalhau integration

## Deployment Philosophy

**CRITICAL**: This project uses immutable infrastructure. ALWAYS destroy and recreate instances when testing changes. Never patch running instances.

### Standard Development Workflow
```bash
# 1. Make changes to deployment code
# 2. Destroy ALL existing instances
uv run -s deploy_spot.py destroy

# 3. Verify cleanup
uv run -s deploy_spot.py list  # Should be empty

# 4. Deploy fresh instances
uv run -s deploy_spot.py create

# 5. Test deployment
./debug_deployment.sh <new-instance-ip>
```

## Development Commands

### Basic Usage
```bash
# Setup configuration
uv run -s deploy_spot.py setup

# Deploy instances (hands-off approach)
uv run -s deploy_spot.py create
# Note: After creation, instances configure themselves autonomously
# Check back in ~5 minutes for fully configured instances

# List running instances
uv run -s deploy_spot.py list

# Destroy all instances
uv run -s deploy_spot.py destroy

# Get help
uv run -s deploy_spot.py help
```

### Advanced VPC Cleanup
```bash
# Scan VPCs (dry run)
uv run -s delete_vpcs.py --dry-run

# Full cleanup
uv run -s delete_vpcs.py
```

### Testing
```bash
# Run full test suite
uv run python test_simple.py

# Test node identity generation
uv run python test_identity_generation.py

# Test sensor integration
uv run python test_sensor_integration.py
```

### Code Quality
```bash
# Linting - ALWAYS run before committing
uv run ruff check deploy_spot.py

# Auto-fix linting issues where possible
uv run ruff check deploy_spot.py --fix

# Type checking (uses full type annotations)
python -m pyright deploy_spot.py
```

**Important:** Always run `uv run ruff check deploy_spot.py` to verify syntax and code quality before committing changes. This is a project requirement.

## Core Components

### Main Entry Points
- `deploy_spot.py` - Primary deployment tool (820 lines)
- `delete_vpcs.py` - Advanced VPC cleanup utility
- `test_simple.py` - Test suite (17 tests)
- `test_identity_generation.py` - Node identity tests

### Key Classes
- `SimpleConfig` - YAML configuration management
- `SimpleStateManager` - JSON-based instance state tracking
- `DeploymentManager` - Main deployment orchestration
- `NodeIdentityGenerator` - Deterministic sensor identity creation (in `generate_node_identity.py`)

### File Layout
```
├── deploy_spot.py              # Main deployment tool
├── delete_vpcs.py              # VPC cleanup utility
├── test_*.py                   # Test suites
├── config.yaml                 # Runtime configuration
├── config.yaml.example         # Comprehensive example
├── instances.json              # Runtime state (auto-created)
├── .aws_cache/                # AMI cache directory
├── files/                     # Files to upload to instances
├── instance/
│   ├── scripts/
│   │   ├── startup.py         # Main startup script
│   │   ├── generate_node_identity.py  # Identity generator
│   │   ├── generate_demo_identity.py  # Demo identity generator
│   │   └── bacalhau-startup.service   # Systemd service
│   └── config/                # Bacalhau configuration templates
└── NODE_IDENTITY_SYSTEM.md    # Identity system documentation
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
2. The `bacalhau.service` runs `set_bacalhau_env.sh` which:
   - Reads the credential files
   - Creates a `.bacalhau.env` file with environment variables
3. Docker Compose loads these environment variables:
   - `BACALHAU_COMPUTE_ORCHESTRATORS` - The orchestrator endpoint
   - `BACALHAU_COMPUTE_AUTH_TOKEN` - The authentication token

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

### Testing Strategy
- Unit tests for all core components
- Mock AWS services for offline testing
- Performance benchmarks included
- Integration tests for real AWS usage
- Determinism tests for identity generation

## Common Development Tasks

### Adding New Features
1. Follow single-file design pattern
2. Add corresponding tests in appropriate test file
3. Update configuration schema if needed
4. Test with real AWS resources

### Debugging
- **IMPORTANT**: Never debug by patching instances
- Use `./debug_deployment.sh <ip>` to collect diagnostics
- Fix issues in source code
- Destroy all instances: `uv run -s deploy_spot.py destroy`
- Deploy fresh: `uv run -s deploy_spot.py create`
- Check `instances.json` for state issues
- Use `--dry-run` with VPC cleanup for safety
- Verify deployment log at `/opt/deployment.log`

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
- Add new cities/manufacturers in `generate_node_identity.py`/I want you to look through this codebase and develop a list of targeted things to ultimately debug what is going on right now. The deployment of the machines  │
│   is working well, but every step along the way, we see we're running into a problem where the code is not ultimately working end-to-end.                        │
│                                                                                                                                                                  │
│   Right now, the machines are being provisioned and rebooted. The directories aren't being created, the startup script isn't working, individual line items in   │
│   the startup script aren't working, and so on. I want you to create a specific test list to go through one-at-a-time to test it.