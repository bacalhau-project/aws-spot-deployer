# Quick Start Guide

## 1. Setup AWS Credentials

For AWS SSO (recommended):
```bash
aws sso login
```

For traditional credentials:
```bash
aws configure
```

## 2. Pull the Docker Image

```bash
docker pull ghcr.io/bacalhau-project/spot-deployer:latest
```

## 3. Create Configuration

```bash
# Create a new config file
docker run --rm -v $(pwd):/app/output ghcr.io/bacalhau-project/spot-deployer setup

# Edit the config.yaml to your needs
nano config.yaml
```

## 4. Deploy Spot Instances

### Basic Deployment
```bash
docker run --rm \
  -v ~/.aws:/root/.aws:ro \
  -v $(pwd)/config.yaml:/app/config/config.yaml:ro \
  ghcr.io/bacalhau-project/spot-deployer create
```

### With Bacalhau Support
```bash
# Create credential files
mkdir -p files
echo "nats://your-orchestrator:4222" > files/orchestrator_endpoint
echo "your-auth-token" > files/orchestrator_token

# Deploy with credentials
docker run --rm \
  -v ~/.aws:/root/.aws:ro \
  -v $(pwd)/config.yaml:/app/config/config.yaml:ro \
  -v $(pwd)/files:/app/files:ro \
  ghcr.io/bacalhau-project/spot-deployer create
```

## 5. Manage Instances

### List Running Instances
```bash
docker run --rm \
  -v ~/.aws:/root/.aws:ro \
  -v $(pwd)/config.yaml:/app/config/config.yaml:ro \
  ghcr.io/bacalhau-project/spot-deployer list
```

### Destroy All Instances
```bash
docker run --rm \
  -v ~/.aws:/root/.aws:ro \
  -v $(pwd)/config.yaml:/app/config/config.yaml:ro \
  ghcr.io/bacalhau-project/spot-deployer destroy
```

## Using the Wrapper Script

For convenience, download and use the wrapper script:

```bash
# Download once
curl -O https://raw.githubusercontent.com/bacalhau-project/spot/main/spot-docker
chmod +x spot-docker

# Then use simple commands
./spot-docker setup
./spot-docker create
./spot-docker list
./spot-docker destroy
```

## Tips

- The container is stateless - all state is stored in AWS
- You can run commands from any machine with the same config
- Use `:ro` for read-only mounts to improve security
- Check deployment status with the debug script if needed
- Add custom setup commands by creating `additional_commands.sh` in your working directory
