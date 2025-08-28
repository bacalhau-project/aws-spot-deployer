# 🌍 SkyPilot Spot Deployer - Deploy Global Clusters with One Command

**Python-powered worldwide deployment of Bacalhau compute nodes using SkyPilot.**

Deploy Bacalhau compute nodes instantly across global cloud regions. Built with modern Python tooling for reliability and maintainability.

## 🚀 **One-Command Global Deployment**

Deploy clusters across worldwide regions with a single command:

```bash
# Install and run instantly with uvx (no local setup required)
uvx run spot-deployer create

# Check status
uvx run spot-deployer status

# View logs
uvx run spot-deployer logs

# SSH to cluster
uvx run spot-deployer ssh

# Clean up
uvx run spot-deployer destroy
```

## ✨ **PyPI Package Architecture**

### 🌟 **Zero Setup Required**
- **uvx execution**: No installation or environment setup needed
- **Python packaging**: Clean Click-based CLI with Rich output
- **Direct deployment**: Uses SkyPilot directly without containers
- **Cross-platform**: Works on any system with Python 3.9+

### 🔥 **What This Provides**
- ✅ **Instant execution** → `uvx run spot-deployer` works immediately
- ✅ **Rich terminal UI** → Beautiful tables and progress indicators
- ✅ **Proper YAML parsing** → No fragile grep/sed operations
- ✅ **Type safety** → Full type annotations throughout
- ✅ **Maintainable code** → Structured Python instead of bash

### 🎯 **Superior Features**
- **Automatic spot preemption recovery** - Never lose your cluster
- **Built-in health monitoring** - Comprehensive node validation
- **Multi-region deployment** - Distributed across availability zones
- **Cloud-agnostic node identity** - Works on AWS, GCP, Azure
- **Secure credential management** - Never commit secrets

## 🏗️ **Architecture**

### Modern Stack
- **Python Package**: PyPI-distributed Click CLI with Rich output
- **SkyPilot**: Direct cloud orchestration and spot management
- **Bacalhau**: Distributed compute with Docker engine support
- **YAML Processing**: Proper PyYAML parsing instead of bash text manipulation
- **Type Safety**: Full mypy type checking throughout

### Deployment Flow
```
uvx run spot-deployer create → Python CLI → SkyPilot deploy → Health check
```

### Package Architecture
```
PyPI Package (spot-deployer):
├── Click CLI framework
├── Rich terminal UI
├── ClusterManager (Python)
├── YAML configuration parsing
├── SkyPilot integration
└── Prerequisites checking
```

## 📋 **Prerequisites**

### Required
- **Python 3.9+** (for uvx, usually already installed)
- **AWS Account** with EC2 permissions
- **AWS Credentials** configured in `~/.aws/credentials` or environment

### Automatic
The CLI automatically handles:
- **SkyPilot installation** and dependency management
- **Prerequisites checking** (AWS access, SkyPilot setup)
- **YAML configuration** parsing and validation
- **File synchronization** to remote nodes

## 🎛️ **Configuration**

### Credential Setup
Create these files in the project directory before deployment:

```bash
# Required credential files
mkdir -p credentials/

# Bacalhau orchestrator endpoint
echo "nats://your-orchestrator.example.com:4222" > credentials/orchestrator_endpoint

# Bacalhau authentication token
echo "your-secret-token" > credentials/orchestrator_token

# AWS credentials for S3 access (optional)
cp ~/.aws/credentials credentials/aws-credentials
```

### Deployment Settings
Edit `cluster.yaml` to customize:

```yaml
name: databricks-wind-farm-cluster

# Global deployment - one node per zone across the world
num_nodes: 9

resources:
  infra: aws
  instance_type: t3.medium
  use_spot: true
  disk_size: 30

# Files to deploy to each node
file_mounts:
  /tmp/credentials/orchestrator_endpoint: ./credentials/orchestrator_endpoint
  /tmp/credentials/orchestrator_token: ./credentials/orchestrator_token
  # ... other files

# Environment variables for deployment
envs:
  DEPLOYMENT_PROJECT: "databricks-wind-farm-cluster"
  BACALHAU_DATA_DIR: "/bacalhau_data"
  # ... other env vars
```

## 🔧 **Commands**

### Core Operations
```bash
# Deploy cluster across global regions
uvx run spot-deployer create

# Check cluster status and health
uvx run spot-deployer status

# List all nodes with details
uvx run spot-deployer list

# View deployment logs
uvx run spot-deployer logs

# SSH to cluster head node
uvx run spot-deployer ssh

# Destroy entire cluster
uvx run spot-deployer destroy

# Clean up local Docker resources
uvx run spot-deployer cleanup

# Check prerequisites and configuration
uvx run spot-deployer check

# Show version
uvx run spot-deployer --version

# Show help
uvx run spot-deployer --help
```

### Advanced Options
```bash
# Custom config file
uvx run spot-deployer create -c my-config.yaml

# Show logs to console instead of log file
uvx run spot-deployer create --console

# Custom log file location
uvx run spot-deployer create --log-file deployment.log
```

## 🧪 **Local Development & Testing**

### Quick Test
```bash
# Test the CLI without installation
uvx run spot-deployer --version

# Check prerequisites
uvx run spot-deployer check

# Test with dry run (if available)
uvx run spot-deployer create --help
```

### Local Development
```bash
# Clone the repository for development
git clone <repository-url>
cd bacalhau-skypilot

# Install in development mode with uv
uv pip install -e .

# Run locally during development
python -m spot_deployer.cli --version

# Run tests
uv run pytest

# Run linting
uv run ruff check .
```

### Debug Deployment
```bash
# Enable console logging for debugging
uvx run spot-deployer create --console

# Check SkyPilot status
uvx run spot-deployer status

# View detailed logs
uvx run spot-deployer logs

# SSH to node for debugging
uvx run spot-deployer ssh
```

### Test Individual Components
```bash
# Test node identity generation
INSTANCE_ID=i-test123 ./scripts/generate_node_identity.py

# Test Bacalhau config generation
./scripts/generate_bacalhau_config.py

# Test health check script
./scripts/health_check.sh
```

## 🌐 **Multi-Cloud Support**

### Current Support
- **AWS**: Full support with spot instances, auto-recovery
- **GCP, Azure**: SkyPilot supports them, configuration needed

### Cloud Provider Detection
```bash
# AWS: Uses IMDS for instance metadata
curl -s http://169.254.169.254/latest/meta-data/instance-id

# Node identity automatically detects cloud provider
# and generates appropriate sensor identities
```

## 📊 **Monitoring & Health**

### Built-in Health Checks
Every deployment includes comprehensive monitoring:

- **Docker service status**
- **Container health** (Bacalhau + Sensor)
- **Network connectivity** (API ports 1234, 4222)
- **File system status** (configs, data directories)
- **Resource utilization** (disk, memory)
- **Orchestrator connectivity**
- **Log analysis** (error detection)

### Status Dashboard
```bash
# View cluster overview
./cluster-deploy status

# Detailed health report via logs
./cluster-deploy logs

# SSH to specific node for debugging
./cluster-deploy ssh
```

## 🔒 **Security**

### Credential Management
- **Never committed to git** - credentials/ in .gitignore
- **Docker volume mounts** for secure credential access
- **Encrypted in transit** - HTTPS/TLS everywhere
- **Least privilege** - minimal required permissions

### Container Security
- **Official SkyPilot image** - berkeley/skypilot
- **Read-only mounts** where possible
- **Isolated container environment**
- **Automatic container cleanup**

## 🚀 **Performance**

### Deployment Speed
- **~5-10 minutes** for 9-node global cluster deployment
- **Parallel deployment** across regions via SkyPilot
- **Docker container reuse** - fast subsequent deployments

### Resource Efficiency
- **t3.medium instances** (2 vCPU, 4GB RAM)
- **30GB disk** per node
- **Spot pricing** - up to 90% cost savings
- **Automatic spot recovery** - SkyPilot handles preemptions

### Reliability
- **Docker container isolation** - consistent environment
- **Health monitoring** with automatic restart
- **Multi-region distribution** for availability
- **SkyPilot retry logic** for transient failures

## 🆘 **Troubleshooting**

### Common Issues

#### 1. Docker Not Running
```bash
# Check Docker status
docker --version
docker info

# Start Docker (varies by OS)
# macOS: Open Docker Desktop
# Linux: sudo systemctl start docker
```

#### 2. AWS Credentials
```bash
# Check AWS access through container
docker exec skypilot-cluster-deploy aws sts get-caller-identity

# Configure if needed
aws configure
# or
aws sso login
```

#### 3. Container Issues
```bash
# Check container status
docker ps --filter name=skypilot-cluster-deploy

# View container logs
docker logs skypilot-cluster-deploy

# Restart container
./cluster-deploy cleanup
./cluster-deploy status  # This will restart the container
```

#### 4. SkyPilot Issues
```bash
# Check SkyPilot through container
docker exec skypilot-cluster-deploy sky check

# View cluster status
docker exec skypilot-cluster-deploy sky status

# Reset cluster if needed
docker exec skypilot-cluster-deploy sky down --all --yes
```

### Debug Commands
```bash
# Verbose deployment
bash -x ./cluster-deploy create

# Direct SkyPilot commands
docker exec skypilot-cluster-deploy sky status --refresh

# SSH to node for debugging
./cluster-deploy ssh
# Then run: sudo docker ps, sudo docker logs <container>
```

## 🤝 **Contributing**

### Development Setup
```bash
git clone <repository-url>
cd bacalhau-skypilot

# Ensure Docker is running
docker --version

# Test the script
./cluster-deploy help
```

### Testing Changes
1. **Local testing**: Use `./cluster-deploy status` to test Docker setup
2. **Configuration test**: Modify `cluster.yaml` and test parsing
3. **Single node test**: Deploy to one region first
4. **Full cluster test**: Test complete 9-node deployment

### Code Standards
- **Docker-first** - all SkyPilot operations via container
- **Shell scripting** - bash with proper error handling
- **Volume mounts** - leverage Docker for isolation
- **SkyPilot native** - use SkyPilot capabilities fully

## 📄 **License**

MIT License - see [LICENSE](LICENSE) for details.

## 🔗 **Links**

- **SkyPilot Documentation**: https://docs.skypilot.co/
- **Bacalhau Documentation**: https://docs.bacalhau.org/
- **Docker Documentation**: https://docs.docker.com/

---

**Ready to deploy?** Ensure Docker is running, then: `./cluster-deploy create`
