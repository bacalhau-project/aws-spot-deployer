# Portable AWS Spot Instance Deployment Tool

This directory contains a portable, self-contained version of the AWS Spot Instance Deployment Tool for Bacalhau clusters. It's designed to be easily shared and requires minimal setup for new users.

## 🚀 Quick Start

### Option 1: Automated Installation (Recommended)

```bash
# Download and run the installation script
./install.sh
```

The installation script will:
- Install UV package manager if needed
- Check AWS CLI availability
- Generate SSH keys if missing
- Setup environment and configuration template
- Run validation tests

### Option 2: Manual Setup

```bash
# 1. Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Make the deployment script executable
chmod +x deploy_spot_portable.py

# 3. Setup environment
./deploy_spot_portable.py --action setup

# 4. Copy configuration template
cp config.yaml_example config.yaml

# 5. Edit configuration (see Configuration section below)
nano config.yaml

# 6. Validate setup
./deploy_spot_portable.py --action validate
```

## 📋 Prerequisites

1. **AWS CLI** configured with credentials
   ```bash
   aws configure
   ```

2. **SSH Key Pair** for instance access
   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519
   ```

3. **UV Package Manager** (automatically installed by install.sh)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

## 🔧 Configuration

Edit `config.yaml` with your specific settings:

```yaml
aws:
  total_instances: 3
  username: bacalhau-runner
  public_ssh_key_path: ~/.ssh/id_ed25519.pub
  private_ssh_key_path: ~/.ssh/id_ed25519

bacalhau:
  orchestrators:
    - nats://your-orchestrator.example.com:4222
  token: your_bacalhau_network_token
  tls: true

regions:
  - us-west-2:
      image: auto
      machine_type: t3.medium
      node_count: auto
  # ... more regions
```

### Key Configuration Options

- **`total_instances`**: Maximum number of instances across all regions
- **`orchestrators`**: Bacalhau NATS orchestrator URLs
- **`token`**: Bacalhau network authentication token
- **`ssh_key_path`**: Path to your SSH private/public key pair
- **`machine_type`**: EC2 instance type (auto-selected for optimal cost)
- **`image`**: AMI ID (auto-detected for Ubuntu 22.04 LTS)

## 📝 Usage

### Available Commands

```bash
# Environment Setup
./deploy_spot_portable.py --action setup      # Setup environment (regions, AMIs, config)
./deploy_spot_portable.py --action verify     # Verify configuration
./deploy_spot_portable.py --action validate   # Run validation tests

# Instance Management (Note: Not yet implemented in portable version)
./deploy_spot_portable.py --action create     # Deploy spot instances
./deploy_spot_portable.py --action list       # List running instances
./deploy_spot_portable.py --action status     # Check status
./deploy_spot_portable.py --action destroy    # Terminate instances
./deploy_spot_portable.py --action cleanup    # Complete cleanup
```

### Typical Workflow

1. **Initial Setup**
   ```bash
   ./install.sh
   # Edit config.yaml with your settings
   ```

2. **Validation**
   ```bash
   ./deploy_spot_portable.py --action validate
   ```

3. **Deployment** (when implemented)
   ```bash
   ./deploy_spot_portable.py --action create
   ```

4. **Management**
   ```bash
   ./deploy_spot_portable.py --action list
   ./deploy_spot_portable.py --action status
   ```

5. **Cleanup**
   ```bash
   ./deploy_spot_portable.py --action destroy    # Instances only
   ./deploy_spot_portable.py --action cleanup    # Everything
   ```

## 🔍 Validation Tests

The tool includes built-in validation tests:

```bash
./deploy_spot_portable.py --action validate
```

Tests include:
- ✅ Environment validation (UV, AWS CLI, credentials)
- ✅ Configuration file loading and parsing
- ✅ AWS connectivity and permissions
- ✅ SSH key availability and format
- ✅ Region and instance type compatibility

## 📦 Distribution

### For Sharing with Others

The portable version consists of just a few files:

```
aws-spot-deployment/
├── deploy_spot_portable.py    # Main deployment script
├── install.sh                 # Installation automation
├── config.yaml_example        # Configuration template
└── PORTABLE_DISTRIBUTION.md   # This documentation
```

### Distribution Methods

1. **Git Repository**
   ```bash
   git clone <repository-url>
   cd aws-spot-deployment
   ./install.sh
   ```

2. **File Archive**
   ```bash
   # Create distribution archive
   tar -czf aws-spot-deployment.tar.gz deploy_spot_portable.py install.sh config.yaml_example PORTABLE_DISTRIBUTION.md
   
   # Extract and use
   tar -xzf aws-spot-deployment.tar.gz
   cd aws-spot-deployment
   ./install.sh
   ```

3. **Single Script Distribution**
   ```bash
   # Just copy the main script
   curl -O https://raw.githubusercontent.com/your-repo/deploy_spot_portable.py
   chmod +x deploy_spot_portable.py
   ./deploy_spot_portable.py --action setup
   ```

## 🔒 Security Considerations

- **Never commit AWS credentials** or Bacalhau tokens to version control
- **Use environment variables** for sensitive configuration:
  ```bash
  export BACALHAU_TOKEN="your_token_here"
  export AWS_ACCESS_KEY_ID="your_key_here"
  export AWS_SECRET_ACCESS_KEY="your_secret_here"
  ```
- **SSH keys** should have appropriate permissions (600 for private, 644 for public)
- **VPC security groups** are automatically configured with minimal required access

## 🐛 Troubleshooting

### Common Issues

1. **UV not found**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   export PATH="$HOME/.cargo/bin:$PATH"
   ```

2. **AWS credentials not configured**
   ```bash
   aws configure
   # or
   export AWS_ACCESS_KEY_ID="your_key"
   export AWS_SECRET_ACCESS_KEY="your_secret"
   ```

3. **SSH permission denied**
   ```bash
   chmod 600 ~/.ssh/id_ed25519
   chmod 644 ~/.ssh/id_ed25519.pub
   ```

4. **No suitable regions found**
   ```bash
   ./deploy_spot_portable.py --action setup  # Refresh region data
   ```

### Debug Logging

Debug information is logged to `debug_deploy_spot.log`:

```bash
tail -f debug_deploy_spot.log
```

## 🔄 Migration from Original Version

If migrating from the original multi-file version:

1. **Backup existing configuration**
   ```bash
   cp config.yaml config.yaml.backup
   ```

2. **Run portable setup**
   ```bash
   ./deploy_spot_portable.py --action setup
   ```

3. **Merge configurations**
   ```bash
   # Copy your custom settings from config.yaml.backup to config.yaml
   ```

4. **Validate new setup**
   ```bash
   ./deploy_spot_portable.py --action validate
   ```

## 🆘 Support

If you encounter issues:

1. **Check validation output**
   ```bash
   ./deploy_spot_portable.py --action validate
   ```

2. **Review debug logs**
   ```bash
   cat debug_deploy_spot.log
   ```

3. **Verify AWS permissions**
   ```bash
   aws sts get-caller-identity
   aws ec2 describe-regions
   ```

4. **Test network connectivity**
   ```bash
   curl -I https://aws.amazon.com
   ```

## 📋 Development Notes

This portable version consolidates the original multi-module architecture into a single script while maintaining all core functionality. The approach was chosen for:

- ✅ **Easy distribution** - single file sharing
- ✅ **Minimal dependencies** - only UV required
- ✅ **Self-contained** - no external module imports
- ✅ **Configuration-driven** - external YAML for settings
- ✅ **Modern tooling** - UV for dependency management

For advanced use cases or development, consider using the original multi-module version in the parent directory.