# Spot Deployer - AWS Spot Instance Deployment Tool

A production-ready tool for deploying AWS spot instances with Bacalhau compute nodes. Features beautiful Rich terminal UI, hands-off deployment, and comprehensive state management.

## 🚀 Quick Start

```bash
# Pull the Docker image
docker pull ghcr.io/bacalhau-project/spot-deployer:latest

# Create configuration
docker run --rm -v $(pwd):/app/output ghcr.io/bacalhau-project/spot-deployer setup

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

The container supports three authentication methods:

1. **Mounted AWS Directory** (Recommended):
   ```bash
   docker run --rm -v ~/.aws:/root/.aws:ro ...
   ```

2. **Environment Variables**:
   ```bash
   docker run --rm \
     -e AWS_ACCESS_KEY_ID=xxx \
     -e AWS_SECRET_ACCESS_KEY=yyy \
     -e AWS_DEFAULT_REGION=us-west-2 ...
   ```

3. **IAM Role** (for EC2/ECS environments)

### Configuration

1. **Generate Config**:
   ```bash
   docker run --rm \
     -v $(pwd):/app/output \
     ghcr.io/bacalhau-project/spot-deployer setup
   ```

2. **Edit `config.yaml`**:
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
  ghcr.io/bacalhau-project/spot-deployer create
```

### Convenience Wrapper

Use the included wrapper script for easier commands:

```bash
# Download wrapper
curl -O https://raw.githubusercontent.com/bacalhau-project/spot/main/spot-docker
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

## 📁 Configuration Options

See [config.yaml.example](config.yaml.example) for all available options:

- Instance types and counts
- Region selection
- VPC configuration
- SSH key settings
- Bacalhau integration
- Custom scripts

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