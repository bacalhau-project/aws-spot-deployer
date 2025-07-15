# AWS Spot Instance Deployer - Simplified

A simple, maintainable tool for deploying AWS spot instances with beautiful Rich output. This tool was simplified from a complex 2400+ line codebase to a clean, single-file implementation focusing on core functionality while maintaining professional output styling.

## Quick Start

### Prerequisites

1. **AWS Account** with permissions to create EC2 instances, VPCs, and security groups
2. **AWS CLI** installed and configured
3. **Python 3.11+** (handled automatically by `uv`)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd spot/

# The tool is ready to use - no installation needed!
```

### Usage

```bash
# 1. Setup basic configuration
uv run -s deploy_spot.py setup

# 2. Deploy spot instances
uv run -s deploy_spot.py create

# 3. List running instances (beautiful Rich table)
uv run -s deploy_spot.py list

# 4. Destroy instances and clean up ALL resources
uv run -s deploy_spot.py destroy

# 5. Get help (styled Rich panel)
uv run -s deploy_spot.py help
```

## Commands

| Command | Description |
|---------|-------------|
| `setup` | Create basic configuration file |
| `create` | Deploy spot instances across regions |
| `list` | List all managed instances with Rich table |
| `destroy` | Terminate instances and clean up ALL resources |
| `help` | Show styled help information |

### Advanced VPC Cleanup

For comprehensive VPC cleanup with detailed progress tracking:

```bash
# Scan for VPCs (dry run)
uv run -s delete_vpcs.py --dry-run

# Full VPC cleanup
uv run -s delete_vpcs.py
```

## Configuration

After running `setup`, you'll have a `config.yaml` file:

```yaml
aws:
  total_instances: 3
  username: ubuntu
regions:
- us-west-2:
    image: auto
    machine_type: t3.medium
- us-east-1:
    image: auto
    machine_type: t3.medium
- eu-west-1:
    image: auto
    machine_type: t3.medium
```

### Configuration Options

- `total_instances`: Number of instances to create across all regions
- `username`: SSH username for instances (default: ubuntu)
- `ssh_key_name`: Optional SSH key name for access
- `regions`: List of regions with instance types

## Features

- **Single File**: Everything in one maintainable file
- **Beautiful Output**: Rich library for colorful tables and styled output
- **Auto-Discovery**: Automatically finds VPCs and subnets
- **AMI Lookup**: Gets latest Ubuntu 22.04 LTS AMIs
- **Caching**: Caches AMI lookups for faster deployment
- **JSON State**: Simple JSON-based instance tracking
- **Error Handling**: Graceful error handling and user feedback
- **Multi-Region**: Deploy across multiple AWS regions

## Architecture

The simplified version uses:

- **SimpleConfig**: YAML configuration management
- **SimpleStateManager**: JSON-based instance tracking
- **File-based caching**: Simple timestamp-based cache
- **Rich UI**: Beautiful tables and styled terminal output
- **Direct AWS API calls**: No complex abstraction layers

## Authentication

Ensure your AWS credentials are configured:

```bash
# Using AWS SSO (recommended)
aws sso login

# Or using AWS CLI
aws configure
```

## Example Output

### Rich Table Display

The `list` command shows a beautiful table:

```
                          Managed Instances (1 total)                           
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Instance ID      ┃ Region     ┃ Type     ┃ State ┃ Public IP   ┃ Created     ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ i-0fb9db7c6893e… │ eu-west-1  │ t3.medi… │ running │ 34.244.109… │ 07-08 17:04 │
└──────────────────┴────────────┴──────────┴───────┴─────────────┴─────────────┘
```

### Styled Messages

- ✅ **Success**: Green checkmarks for completed actions
- ❌ **Errors**: Red X marks for failures with guidance
- ℹ️ **Info**: Blue information messages
- ⚠️ **Warnings**: Yellow warning messages

### Example Session

```bash
❯ uv run -s deploy_spot.py create
Creating 3 instances across 3 regions...
Creating 1 instances in us-west-2...
Looking for default VPC in us-west-2...
Using default VPC vpc-0ceb2fcdb2bdc32c7 in us-west-2
...
✅ Created i-00ffe7a302a34784c in eu-west-1
✅ Successfully created 1 instances

❯ uv run -s deploy_spot.py destroy
✅ Terminated 1 instances in eu-west-1
✅ Successfully terminated 1 instances
```

## How It Works

1. **Configuration**: Loads settings from `config.yaml`
2. **Authentication**: Checks AWS credentials early
3. **Region Discovery**: Finds available VPCs and subnets
4. **AMI Lookup**: Gets latest Ubuntu AMIs (with caching)
5. **Spot Requests**: Creates spot instance requests
6. **Instance Tracking**: Saves instance details to JSON
7. **Tagging**: Tags instances for management
8. **Rich Output**: Beautiful tables and styled messages

## Troubleshooting

### Common Issues

1. **Authentication Errors**:
   ```bash
   aws sso login
   ```

2. **No AMI Found**: Some regions may not have the specific Ubuntu AMI
   - Tool will skip those regions and continue with others

3. **No VPC Found**: Tool will try to find any available VPC in the region
   - If none found, region will be skipped

4. **Config Not Found**:
   ```bash
   uv run -s deploy_spot.py setup
   ```

### Getting Help

- Run `uv run -s deploy_spot.py help` for usage
- Check `instances.json` for current state
- Check AWS console for actual instance status

## Development

### File Structure

```
├── deploy_spot.py          # Main tool (820 lines) - ALL FUNCTIONALITY
├── test_simple.py          # Test suite (17 tests)
├── delete_vpcs.py          # Advanced VPC cleanup utility
├── config.yaml             # Configuration file
├── instances.json          # Instance state (auto-created)
├── .aws_cache/            # AMI cache directory
└── README.md              # This documentation
```

### Testing

```bash
# Run the test suite
uv run python test_simple.py

# Test individual commands
uv run -s deploy_spot.py setup
uv run -s deploy_spot.py create
uv run -s deploy_spot.py list
uv run -s deploy_spot.py destroy
```

### Code Quality

- **Linting**: `uv run ruff check deploy_spot.py`
- **Type Checking**: Full type annotations
- **Testing**: Comprehensive test suite
- **Documentation**: Clear docstrings

## Performance

- **Startup Time**: 0.146 seconds (93% faster than original)
- **File Size**: 30KB (vs 86KB original) - 65% reduction
- **Line Count**: 820 lines (vs 2400+ original) - 66% reduction
- **Memory Usage**: Significantly reduced
- **Rich Output**: Beautiful tables and styled terminal output
- **Dependencies**: Just 3 packages (boto3, pyyaml, rich)

## Migration from Original

This simplified version maintains all core functionality while removing:

- Complex caching systems
- Multiple abstraction layers
- SQLite database dependency
- Over-engineered validation
- Unnecessary utility functions

If you need the original complex version, check the git history before the simplification.

## Contributing

The focus is on simplicity and maintainability. When contributing:

1. Keep it simple - avoid over-engineering
2. Add tests for new functionality
3. Update documentation
4. Follow the existing code style
5. Test with real AWS resources

## License

[Add your license here]