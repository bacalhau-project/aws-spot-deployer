# AWS Spot Instance Deployment Tool for Bacalhau Clusters

This is a complete deployment tool for setting up Bacalhau compute clusters using AWS spot instances. It automatically finds cost-effective regions, configures optimal instance types, and deploys a complete Bacalhau cluster with minimal effort.

## Quick Start (Binary Distribution)

The fastest way to get started is using the pre-built binary:

### Prerequisites

1. **AWS Account and Credentials**: Active AWS account with permissions to create EC2 instances, VPCs, security groups, etc.
2. **AWS CLI Tools**: Installed and configured with valid credentials.
3. **SSH Key Pair**: For secure access to your instances.

### Download and Setup

1. **Download the binary**: `aws-spot-deployer` (no additional dependencies required)
2. **Make it executable**: `chmod +x aws-spot-deployer`
3. **Configure AWS credentials**:
   ```bash
   aws configure
   # or
   aws sso login
   ```

### Quick Deploy

```bash
# 1. Set up environment (finds regions, gets AMIs, creates config template)
./aws-spot-deployer setup

# 2. Copy and customize configuration
cp config.yaml_example config.yaml
# Edit config.yaml with your Bacalhau orchestrator details

# 3. Verify setup
./aws-spot-deployer verify

# 4. Deploy your cluster
./aws-spot-deployer create

# 5. Check status
./aws-spot-deployer list

# 6. When finished, clean up
./aws-spot-deployer destroy
```

That's it! Your Bacalhau cluster is now running on cost-effective spot instances. 

## Configuration

The tool uses a `config.yaml` file for all settings. After running `setup`, you'll have a `config.yaml_example` file to customize:

### Basic Configuration
```yaml
aws:
  total_instances: 3                    # Total instances across all regions
  username: bacalhau-runner            # SSH username for instances
  public_ssh_key_path: ~/.ssh/id_ed25519.pub
  private_ssh_key_path: ~/.ssh/id_ed25519

bacalhau:
  orchestrators: 
    - nats://your-orchestrator:4222    # Bacalhau NATS endpoints
  token: your_network_token            # Authentication token
  tls: true                           # Use TLS for connections

regions:
  - us-west-2:
      image: auto                      # Auto-select Ubuntu AMI
      machine_type: t3.medium         # Instance type
      node_count: auto                # Auto-distribute instances
```

**Important**: 
- Replace `your-orchestrator:4222` with your actual Bacalhau orchestrator URL
- Replace `your_network_token` with your Bacalhau network token
- Ensure your SSH keys exist and have correct permissions:
  ```bash
  chmod 600 ~/.ssh/id_ed25519
  ```

## Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `setup` | Find available regions, get AMIs, create config template | `./aws-spot-deployer setup` |
| `verify` | Verify configuration and environment | `./aws-spot-deployer verify` |
| `validate` | Run comprehensive validation tests | `./aws-spot-deployer validate` |
| `create` | Deploy spot instances and Bacalhau cluster | `./aws-spot-deployer create` |
| `list` | List all managed spot instances with status | `./aws-spot-deployer list` |
| `status` | Show detailed status of deployment | `./aws-spot-deployer status` |
| `destroy` | Terminate all managed spot instances | `./aws-spot-deployer destroy` |
| `cleanup` | Full cleanup (instances + VPC resources) | `./aws-spot-deployer cleanup` |
| `help` | Show detailed help and usage information | `./aws-spot-deployer help` |

### Command Options

- `--config PATH`: Use custom configuration file (default: `config.yaml`)

Examples:
```bash
./aws-spot-deployer verify --config my-config.yaml
./aws-spot-deployer create --config production.yaml
```

## How It Works

The tool automatically:

1. **Finds Cost-Effective Regions**: Scans all AWS regions for spot instance availability and pricing
2. **Selects Optimal Instance Types**: Chooses the most cost-effective instances that meet minimum requirements
3. **Manages Infrastructure**: Creates VPCs, security groups, and networking automatically
4. **Deploys Bacalhau**: Installs and configures Bacalhau on each instance
5. **Tracks State**: Maintains a local database of all managed instances for easy management

### Key Features

- **Automatic Region Discovery**: No need to manually research which regions have capacity
- **Cost Optimization**: Always selects the cheapest available spot instances
- **Clean Teardown**: Complete cleanup of all AWS resources when finished
- **State Management**: Remembers all deployed instances across restarts
- **Comprehensive Logging**: Detailed logs for troubleshooting (`debug_deploy_spot.log`)

## Troubleshooting

### Common Issues

1. **AWS Authentication Errors**: 
   ```bash
   aws sso login
   # or
   aws configure
   ```

2. **Configuration Issues**: Run validation to diagnose problems
   ```bash
   ./aws-spot-deployer validate
   ```

3. **Spot Capacity Not Available**: The tool will automatically try multiple regions and instance types

4. **Resources Not Fully Cleaned Up**: Use the cleanup command which includes retry logic
   ```bash
   ./aws-spot-deployer cleanup
   ```

### Getting Help

- **Detailed Help**: `./aws-spot-deployer help`
- **Verbose Validation**: `./aws-spot-deployer validate`
- **View Logs**: `cat debug_deploy_spot.log`
- **Check Instance Status**: `./aws-spot-deployer list`

---

## Development and Building (Advanced)

If you want to modify the tool or build it from source, you'll need Python and development dependencies.

### Prerequisites for Development

1. **Python 3.11+**
2. **UV Package Manager**: `pip install uv`
3. **Git**: For cloning the repository

### Development Setup

```bash
# Clone the repository
git clone <repository-url>
cd spot/

# Install development dependencies (handled by UV automatically)
# Dependencies are defined in deploy_spot.py script header

# Run directly from source
uv run -s deploy_spot.py help
```

### Building the Binary

To create a new binary distribution:

```bash
# Run the clean build process (includes smoke tests)
python build_clean.py
```

This will:
1. Run comprehensive smoke tests (18 test cases)
2. Clean old build artifacts
3. Build a fresh binary with PyInstaller
4. Test the resulting binary
5. Output: `./dist/aws-spot-deployer`

### Running Tests

```bash
# Run smoke tests (no AWS calls, uses mocking)
python test_smoke.py

# Or run via the build process
python build_clean.py
```

### Development Commands (Source)

When developing, you can run directly from source:

```bash
# Using UV (recommended)
uv run -s deploy_spot.py setup
uv run -s deploy_spot.py verify
uv run -s deploy_spot.py create

# Using Python directly (requires installing dependencies)
python deploy_spot.py help
```

### Project Structure

```
├── deploy_spot.py           # Main source file (self-contained)
├── aws-spot-deployer.spec   # PyInstaller build specification
├── test_smoke.py           # Comprehensive test suite (18 tests)
├── build_clean.py          # Automated build system
├── config.yaml_example     # Configuration template
└── dist/
    └── aws-spot-deployer   # Compiled binary (26MB)
```

### Code Style

The project follows these conventions:
- **UV Script Headers**: PEP 723 inline dependencies
- **Type Annotations**: Full type hints throughout
- **Async/Await**: Proper concurrency for AWS operations
- **Rich UI**: Terminal interfaces with progress bars and tables
- **Comprehensive Logging**: Debug logging to `debug_deploy_spot.log`
- **Error Handling**: Robust error handling with timeouts and retries