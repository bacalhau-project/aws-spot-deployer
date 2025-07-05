# Bacalhau AWS Spot Cluster Setup Guide

## Commands

### Build/Run/Test
- `uv run -s deploy_spot.py --action setup` - Complete environment setup (regions, AMIs, config)
- `uv run -s deploy_spot.py --action verify` - Verify configuration and environment
- `uv run -s deploy_spot.py --action create` - Deploy spot instances and Bacalhau cluster
- `uv run -s deploy_spot.py --action list` - List running instances (database + AWS status)
- `uv run -s deploy_spot.py --action status` - Comprehensive status check
- `uv run -s deploy_spot.py --action destroy` - Terminate instances only
- `uv run -s deploy_spot.py --action cleanup` - Complete cleanup (instances + VPCs)
- `uv run -s deploy_spot.py --action print-database` - Show database contents

### Individual Utility Commands (Optional)
- `uv run -s util/get_available_regions.py [--show-all]` - Find regions with suitable spot instances
- `uv run -s util/get_ubuntu_amis.py` - Get Ubuntu AMIs for available regions
- `uv run -s util/update_config_with_regions.py` - Update config with available regions
- `uv run -s delete_vpcs.py` - Manual VPC cleanup (integrated in --action cleanup)

### Linting
- `ruff check .` - Run linter on all Python files
- `ruff format .` - Auto-format Python code to match style guidelines

### Alternative (pip)
- `python -m util.get_available_regions [--show-all]`
- `python -m util.get_ubuntu_amis`
- `python -m util.update_config_with_regions`
- `python deploy_spot.py [create|list|destroy|nuke]`

## Code Style Guidelines
- Use f-strings for string formatting
- Use async/await for proper concurrency with task handling and error propagation
- Leverage rich library for terminal UI (progress bars, tables, live displays)
- Implement comprehensive error handling with timeouts and retries for AWS API calls
- Structure logging with levels (DEBUG, INFO, WARNING, ERROR) and consistent formatting
- Follow PEP 8 naming conventions (snake_case for variables/functions, UPPER_CASE for constants)
- Include type annotations for all function parameters and return values
- Design idempotent operations with proper resource cleanup for AWS resources
- Organize code into logical modules (aws/, config/, spot/, ui/ packages)
- Implement proper signal handling and state management for tracking operation progress