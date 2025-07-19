# Docker Usage Guide

## Quick Start

Pull the latest image:
```bash
docker pull ghcr.io/bacalhau-project/spot-deployer:latest
```

## Basic Usage

### 1. Create Configuration

```bash
docker run --rm \
  -v $(pwd):/app/output \
  ghcr.io/bacalhau-project/spot-deployer:latest setup
```

This creates a `config.yaml` in your current directory.

### 2. Deploy Instances

```bash
docker run --rm \
  -v ~/.aws:/root/.aws:ro \
  -v $(pwd)/config.yaml:/app/config/config.yaml:ro \
  -v $(pwd)/files:/app/files:ro \
  ghcr.io/bacalhau-project/spot-deployer:latest create
```

### 3. List Instances

```bash
docker run --rm \
  -v ~/.aws:/root/.aws:ro \
  -v $(pwd)/config.yaml:/app/config/config.yaml:ro \
  ghcr.io/bacalhau-project/spot-deployer:latest list
```

### 4. Destroy Instances

```bash
docker run --rm \
  -v ~/.aws:/root/.aws:ro \
  -v $(pwd)/config.yaml:/app/config/config.yaml:ro \
  ghcr.io/bacalhau-project/spot-deployer:latest destroy
```

## AWS Authentication

The container supports three authentication methods:

### Method 1: Environment Variables

```bash
docker run --rm \
  -e AWS_ACCESS_KEY_ID=your-key-id \
  -e AWS_SECRET_ACCESS_KEY=your-secret-key \
  -e AWS_DEFAULT_REGION=us-west-2 \
  -v $(pwd)/config.yaml:/app/config/config.yaml:ro \
  ghcr.io/bacalhau-project/spot-deployer:latest list
```

### Method 2: Mounted AWS Directory (Recommended)

```bash
docker run --rm \
  -v ~/.aws:/root/.aws:ro \
  -v $(pwd)/config.yaml:/app/config/config.yaml:ro \
  ghcr.io/bacalhau-project/spot-deployer:latest list
```

### Method 3: IAM Role (EC2/ECS)

When running on EC2 or ECS with an IAM role attached:
```bash
docker run --rm \
  -v $(pwd)/config.yaml:/app/config/config.yaml:ro \
  ghcr.io/bacalhau-project/spot-deployer:latest list
```

## Volume Mounts

| Mount Path | Purpose | Required | Mode |
|------------|---------|----------|------|
| `/root/.aws` | AWS credentials | Yes* | Read-only |
| `/app/config/config.yaml` | Spot deployer config | Yes | Read-only |
| `/app/files` | Bacalhau credentials | No | Read-only |
| `/app/output` | Output directory | For setup | Read-write |

*Required unless using environment variables or IAM role

## Bacalhau Credentials

To deploy with Bacalhau support, mount your credential files:

```bash
# Create credential files
mkdir -p files
echo "nats://orchestrator.example.com:4222" > files/orchestrator_endpoint
echo "your-secret-token" > files/orchestrator_token

# Run with credentials
docker run --rm \
  -v ~/.aws:/root/.aws:ro \
  -v $(pwd)/config.yaml:/app/config/config.yaml:ro \
  -v $(pwd)/files:/app/files:ro \
  ghcr.io/bacalhau-project/spot-deployer:latest create
```

## Docker Compose Example

Create a `docker-compose.yml`:

```yaml
version: '3.8'

services:
  spot-deployer:
    image: ghcr.io/bacalhau-project/spot-deployer:latest
    volumes:
      - ~/.aws:/root/.aws:ro
      - ./config.yaml:/app/config/config.yaml:ro
      - ./files:/app/files:ro
      - ./output:/app/output
    environment:
      - AWS_DEFAULT_REGION=us-west-2
    command: ${COMMAND:-help}
```

Then use:
```bash
# Create config
COMMAND=setup docker-compose run --rm spot-deployer

# Deploy
COMMAND=create docker-compose run --rm spot-deployer

# List
COMMAND=list docker-compose run --rm spot-deployer

# Destroy
COMMAND=destroy docker-compose run --rm spot-deployer
```

## State Management

The container is stateless. Instance state is stored in AWS tags and retrieved on each run. This means:
- No persistent volumes needed for state
- Can run from any machine with same config
- Multiple users can manage same deployment

## Troubleshooting

### "No AWS credentials found"
- Check that ~/.aws/credentials exists
- Verify AWS CLI works: `aws sts get-caller-identity`
- Try environment variables method

### "No config file found"
- Ensure config.yaml is mounted correctly
- Check file permissions
- Run setup command first

### "Permission denied"
- Add `:ro` to read-only mounts
- Check file ownership
- Ensure files are readable

### Container Platform Issues
- The image supports both amd64 and arm64
- Docker will automatically pull the correct platform
- Use `--platform` to force a specific architecture

## Advanced Usage

### Custom Entry Point

Override the entrypoint for debugging:
```bash
docker run --rm -it \
  --entrypoint /bin/bash \
  -v ~/.aws:/root/.aws:ro \
  ghcr.io/bacalhau-project/spot-deployer:latest
```

### Environment Variables

Supported environment variables:
- `SPOT_CONFIG_PATH` - Alternative config file path
- `SPOT_FILES_DIR` - Alternative files directory
- `SPOT_OUTPUT_DIR` - Alternative output directory
- `AWS_*` - All standard AWS environment variables

### Building Locally

```bash
# Clone repository
git clone https://github.com/bacalhau-project/spot.git
cd spot

# Build image
./scripts/build-docker.sh

# Test locally
docker run --rm spot-deployer:dev help
```