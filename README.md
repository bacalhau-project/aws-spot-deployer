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

# Automatic script upload during instance creation
startup_script_path: ./startup_script.sh     # Script to auto-upload and execute
files_directory_path: ./files                # Directory with supporting files

regions:
  - us-west-2:
      image: auto                      # Auto-select Ubuntu AMI
      machine_type: t3.medium         # Instance type
      node_count: auto                # Auto-distribute instances
```

### Automatic Script Execution

When you run `create`, the tool automatically:

1. **Detects startup script** at `startup_script_path` (default: `./startup_script.sh`)
2. **Detects files directory** at `files_directory_path` (default: `./files`)  
3. **Creates instances** with standard infrastructure setup
4. **Waits for SSH readiness** (30 seconds)
5. **Automatically uploads and executes** the startup script with files

**Example setup:**
```bash
# Create your startup script
cat > startup_script.sh << 'EOF'
#!/bin/bash
echo "Configuring instance with uploaded files..."
# Access files via $DEPLOY_FILES_DIR environment variable
if [ -d "$DEPLOY_FILES_DIR" ]; then
    echo "Processing $(ls -1 $DEPLOY_FILES_DIR | wc -l) uploaded files"
    # Your custom configuration here
fi
echo "Instance setup completed!"
EOF

# Create files directory with configurations
mkdir files
echo "database_url=postgres://..." > files/config.env
echo "api_key=your-key" > files/credentials.txt

# Deploy - script and files uploaded automatically
./aws-spot-deployer create
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
| `upload-script` | Upload and execute scripts on running instances | `./aws-spot-deployer upload-script ./my_script.sh` |
| `cache` | Manage AWS data cache (refresh, stats, clear) | `./aws-spot-deployer cache stats` |
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
- **Script Upload & Execution**: Deploy and run custom scripts on all instances
- **File Transfer System**: Upload supporting files (credentials, configs) with scripts
- **Comprehensive Logging**: Detailed logs for troubleshooting (`debug_deploy_spot.log`)

## Script Upload & Execution System

After deploying your Bacalhau cluster, you can upload and execute custom scripts on all running instances. This is perfect for deploying additional software, updating configurations, or running maintenance tasks.

### Basic Script Upload

Upload and execute a single script:

```bash
# Upload and run a script on all running instances
./aws-spot-deployer upload-script ./my_maintenance_script.sh

# Example: Update all instances with latest security patches
./aws-spot-deployer upload-script ./update_system.sh
```

### Advanced: Script + Supporting Files

For complex deployments that need supporting files (credentials, configurations, data files), use the files directory system:

```bash
# 1. Create a files directory with supporting files
mkdir ./files
cp database.config ./files/
cp api_credentials.json ./files/
cp deployment_data.csv ./files/

# 2. Upload script - files are automatically uploaded first
./aws-spot-deployer upload-script ./deploy_application.sh
```

**How it works:**
1. Tool automatically detects `./files` directory
2. Creates unique temporary directory on each instance (`/tmp/deploy_files_<timestamp>_<pid>`)
3. Uploads all files from `./files` to the temporary directory
4. Runs your script with `DEPLOY_FILES_DIR` environment variable pointing to uploaded files
5. Your script can access files: `cat $DEPLOY_FILES_DIR/database.config`

### Script Examples

**Basic System Update Script** (`update_system.sh`):
```bash
#!/bin/bash
echo "Updating system packages..."
sudo apt update && sudo apt upgrade -y
echo "System update completed on $(hostname)"
```

**Application Deployment with Files** (`deploy_app.sh`):
```bash
#!/bin/bash
echo "Deploying application with configuration files..."

# Access uploaded files
CONFIG_FILE="$DEPLOY_FILES_DIR/app.config"
CREDENTIALS="$DEPLOY_FILES_DIR/api_credentials.json"

if [ -f "$CONFIG_FILE" ]; then
    echo "Found configuration file, copying to /etc/myapp/"
    sudo mkdir -p /etc/myapp
    sudo cp "$CONFIG_FILE" /etc/myapp/
fi

if [ -f "$CREDENTIALS" ]; then
    echo "Found credentials, setting up API access..."
    sudo cp "$CREDENTIALS" /etc/myapp/credentials.json
    sudo chmod 600 /etc/myapp/credentials.json
fi

echo "Application deployment completed"
```

### File Upload Features

- **Automatic Detection**: Detects `./files` directory automatically
- **Preserves Structure**: Maintains file organization and permissions
- **Efficient Transfer**: Uses tar compression for fast upload
- **Unique Isolation**: Each upload gets unique temporary directory
- **Environment Integration**: `DEPLOY_FILES_DIR` variable available in scripts
- **Progress Tracking**: Real-time progress bars for uploads and execution
- **Error Handling**: Comprehensive error reporting for failed transfers

### Common Use Cases

1. **Configuration Management**: Deploy updated config files across cluster
2. **Credential Distribution**: Securely distribute API keys or certificates  
3. **Data Deployment**: Upload datasets or reference files
4. **Software Installation**: Deploy custom applications with dependencies
5. **Maintenance Tasks**: Run system updates or health checks
6. **Monitoring Setup**: Deploy monitoring agents with configurations

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

5. **Script Upload Failures**: Check SSH connectivity and key permissions
   ```bash
   # Test SSH connection manually
   ssh -i ~/.ssh/id_ed25519 ubuntu@<instance-ip>
   
   # Check key permissions (should be 600)
   chmod 600 ~/.ssh/id_ed25519
   ```

6. **Files Not Found in Script**: Verify DEPLOY_FILES_DIR environment variable
   ```bash
   # In your script, debug with:
   echo "Files directory: $DEPLOY_FILES_DIR"
   ls -la "$DEPLOY_FILES_DIR"
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
uv run -s deploy_spot.py upload-script ./my_script.sh

# Using Python directly (requires installing dependencies)
python deploy_spot.py help
```

### Project Structure

```
├── deploy_spot.py                      # Main source file (self-contained)
├── aws-spot-deployer.spec              # PyInstaller build specification
├── test_smoke.py                       # Comprehensive test suite (42 tests)
├── build_clean.py                      # Automated build system
├── config.yaml_example                 # Basic configuration template
├── config_with_auto_upload_example.yaml # Full config with auto-upload settings
├── startup_script.sh                   # Default auto-upload script
├── test_upload_script.sh               # Basic test script
├── deploy_with_files_example.sh        # Advanced example with files
├── files/                              # Optional directory for supporting files
│   ├── credentials.json                # Example: API credentials
│   ├── app.config                     # Example: Application configuration
│   └── deployment_data.csv            # Example: Data files
└── dist/
    └── aws-spot-deployer              # Compiled binary (26MB)
```

### Code Style

The project follows these conventions:
- **UV Script Headers**: PEP 723 inline dependencies
- **Type Annotations**: Full type hints throughout
- **Async/Await**: Proper concurrency for AWS operations
- **Rich UI**: Terminal interfaces with progress bars and tables
- **Comprehensive Logging**: Debug logging to `debug_deploy_spot.log`
- **Error Handling**: Robust error handling with timeouts and retries