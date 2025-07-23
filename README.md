# Spot Deployer - AWS Spot Instance Deployment Tool

A production-ready tool for deploying AWS spot instances with Bacalhau compute nodes. Features beautiful Rich terminal UI, hands-off deployment, and comprehensive state management.

## 🚀 Quick Start

### One-liner Installation (Recommended)

```bash
# Deploy spot instances with a single command!
curl -sSL https://bacalhau-project.github.io/aws-spot-deployer/install.sh | bash -s -- create

# Or use the short URL (if configured)
curl -sSL https://bac.al/spot | bash -s -- create
```

The installer will:

- Check prerequisites (Docker, AWS credentials)
- Set up configuration directory at `~/.spot-deployer`
- Pull the latest Docker image
- Run the deployment

#### Available Commands

```bash
# Initial setup - creates default configuration
curl -sSL https://bac.al/spot | bash -s -- setup

# Create spot instances
curl -sSL https://bac.al/spot | bash -s -- create

# List running instances
curl -sSL https://bac.al/spot | bash -s -- list

# Destroy all instances
curl -sSL https://bac.al/spot | bash -s -- destroy

# Use specific version
curl -sSL https://bac.al/spot | bash -s -- create --version 1.0.0

# Dry run - see what would happen
curl -sSL https://bac.al/spot | bash -s -- create --dry-run
```

### Manual Docker Usage

```bash
# Pull the Docker image
docker pull ghcr.io/bacalhau-project/aws-spot-deployer:latest

# Create configuration
docker run --rm -v $(pwd):/app/output ghcr.io/bacalhau-project/aws-spot-deployer setup

# Deploy instances
docker run --rm \
  -v ~/.aws:/root/.aws:ro \
  -v $(pwd)/config.yaml:/app/config/config.yaml:ro \
  ghcr.io/bacalhau-project/spot-deployer create

# List instances
docker run --rm \
  -v ~/.aws:/root/.aws:ro \
  -v $(pwd)/config.yaml:/app/config/config.yaml:ro \
  ghcr.io/bacalhau-project/spot-deployer list

# Destroy instances
docker run --rm \
  -v ~/.aws:/root/.aws:ro \
  -v $(pwd)/config.yaml:/app/config/config.yaml:ro \
  ghcr.io/bacalhau-project/spot-deployer destroy
```

## 📋 Prerequisites

- **Docker** installed on your machine
- **AWS Account** with EC2, VPC, and Security Group permissions
- **AWS Credentials** configured locally
- **Bacalhau Orchestrator** credentials (optional)

## 🐳 Docker Usage

### AWS Authentication

The spot deployer now includes a unified `spot` command that automatically detects and uses your AWS credentials:

```bash
# The spot command automatically detects your credentials
./spot create

# It will show which credentials are being used:
# 🔍 Detecting AWS credentials...
# ✓ Using AWS SSO session
# → Running: docker run ...
```

**Supported Authentication Methods** (in order of detection):

1. **Environment Variables** - If AWS_ACCESS_KEY_ID is set
2. **EC2 Instance Role** - When running on EC2
3. **AWS SSO** - If you have an active SSO session
4. **AWS Config Files** - ~/.aws/credentials or ~/.aws/config

**Manual Authentication Options**:

1. **AWS SSO** (Recommended):
   ```bash
   # Login with SSO first
   aws sso login

   # Then use spot command
   ./spot create
   ```

2. **Environment Variables**:
   ```bash
   export AWS_ACCESS_KEY_ID=your-key-id
   export AWS_SECRET_ACCESS_KEY=your-secret-key
   ./spot create
   ```

3. **AWS Profile**:
   ```bash
   export AWS_PROFILE=myprofile
   ./spot create
   ```

The tool will display detailed information about which AWS credentials are being used during execution:

```
╭─────────────────── AWS Credentials ───────────────────╮
│ ✓ AWS Authentication Successful                       │
│                                                       │
│ Credential Type: AWS SSO/AssumedRole                  │
│ Credential Source: AWS SSO                            │
│ Identity: AWSReservedSSO_AdministratorAccess_xxx     │
│ Account: 123456789012                                 │
│ Region: us-west-2                                     │
╰───────────────────────────────────────────────────────╯
```

See [AWS_SSO_DOCKER.md](AWS_SSO_DOCKER.md) for additional SSO configuration details.

### Configuration

1. **Generate Config**:

```bash
   docker run --rm \
     -v $(pwd):/app/output \
     ghcr.io/bacalhau-project/aws-spot-deployer setup
```

1. **Edit `config.yaml`**:

```yaml
   aws:
     total_instances: 10
     username: ubuntu
     use_dedicated_vpc: true
   regions:
     - us-west-2:
         machine_type: t3.medium
         image: auto
```

### Bacalhau Integration

For Bacalhau compute nodes:

```bash
# Create credential files
mkdir -p files
echo "nats://orchestrator.example.com:4222" > files/orchestrator_endpoint
echo "your-secret-token" > files/orchestrator_token

# Deploy with credentials
docker run --rm \
  -v ~/.aws:/root/.aws:ro \
  -v $(pwd)/config.yaml:/app/config/config.yaml:ro \
  -v $(pwd)/files:/app/files:ro \
  ghcr.io/bacalhau-project/aws-spot-deployer create
```

### Custom Commands

Run custom setup commands on each instance by creating `additional_commands.sh`:

```bash
# Create custom commands script
cat > additional_commands.sh << 'EOF'
#!/bin/bash
# Custom setup commands run after deployment

echo "[$(date)] Running custom commands"

# Example: Install additional software
sudo apt-get update
sudo apt-get install -y htop iotop

# Example: Configure monitoring
echo "custom-monitoring-config" > /opt/monitoring.conf

# Example: Set up custom environment
echo "export CUSTOM_VAR=value" >> /home/ubuntu/.bashrc

echo "[$(date)] Custom commands completed"
EOF

chmod +x additional_commands.sh

# Deploy with custom commands
docker run --rm \
  -v ~/.aws:/root/.aws:ro \
  -v $(pwd)/config.yaml:/app/config/config.yaml:ro \
  -v $(pwd)/additional_commands.sh:/app/output/additional_commands.sh:ro \
  ghcr.io/bacalhau-project/aws-spot-deployer create
```

The `additional_commands.sh` script will be uploaded to each instance and executed during deployment.

### Convenience Wrapper

Use the included wrapper script for easier commands:

```bash
# Download wrapper
curl -O https://raw.githubusercontent.com/bacalhau-project/aws-spot-deployer/main/spot-docker
chmod +x spot-docker

# Use wrapper
./spot-docker setup
./spot-docker create
./spot-docker list
./spot-docker destroy
```

## 🎨 Features

- **Beautiful Terminal UI** - Rich tables and progress tracking
- **Hands-Off Deployment** - No SSH connection held during setup
- **State Management** - Automatic state tracking via AWS tags
- **Multi-Region** - Deploy across multiple AWS regions
- **Dedicated VPCs** - Isolated network per deployment
- **Bacalhau Ready** - Optional compute node deployment
- **Custom Commands** - Run your own setup scripts on instances

## 📁 Configuration Options

See [config.yaml.example](config.yaml.example) for all available options:

- Instance types and counts
- Region selection
- VPC configuration
- SSH key settings
- Bacalhau integration
- Custom scripts and commands

## 🆘 Troubleshooting

### No AWS Credentials Found

Ensure AWS credentials are available:

```bash
# Check credentials
aws sts get-caller-identity

# Or use environment variables
export AWS_ACCESS_KEY_ID=xxx
export AWS_SECRET_ACCESS_KEY=yyy
```

### No Config File Found

Create a config file first:

```bash
docker run --rm -v $(pwd):/app/output ghcr.io/bacalhau-project/spot-deployer setup
```

### Permission Denied

Ensure proper mount permissions:

- Use `:ro` for read-only mounts
- Check file ownership
- Verify Docker daemon permissions

### Debugging Deployments

Use the debug script after deployment:

```bash
# Download debug script
curl -O https://raw.githubusercontent.com/bacalhau-project/spot/main/debug_deployment.sh
chmod +x debug_deployment.sh

# Run diagnostics
./debug_deployment.sh <instance-ip>
```

## 📦 Version Management

```bash
# Use specific version
docker pull ghcr.io/bacalhau-project/spot-deployer:v1.0.0

# Use latest
docker pull ghcr.io/bacalhau-project/spot-deployer:latest

# Use edge (main branch)
docker pull ghcr.io/bacalhau-project/spot-deployer:edge
```

## 🚦 Development

For development and contributions:

```bash
# Clone repository
git clone https://github.com/bacalhau-project/spot.git
cd spot

# Build Docker image locally
./scripts/build-docker.sh

# Run tests
docker run --rm spot-deployer:dev help
```

## 📄 License

[Your License Here]

## 🤝 Support

- **Issues**: [GitHub Issues](https://github.com/bacalhau-project/spot/issues)
- **Documentation**: [DOCKER_USAGE.md](DOCKER_USAGE.md)
- **Debug Guide**: [DEPLOYMENT_DEBUG_CHECKLIST.md](DEPLOYMENT_DEBUG_CHECKLIST.md)
