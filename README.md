# 🌍 Amauo - AWS Spot Instance Deployment Tool

**Modern AWS spot instance deployment tool** for deploying Bacalhau compute nodes and sensor simulations. Features a clean Python package structure with beautiful Rich terminal output.

Deploy Bacalhau compute nodes across AWS regions using spot instances for cost-effective distributed computing.

## 🚀 **One-Command Global Deployment**

Deploy clusters across worldwide regions with a single command:

```bash
# Install and run instantly with uvx (no local setup required)
uvx amauo create

# Check status
uvx amauo list

# Setup configuration
uvx amauo setup

# Clean up
uvx amauo destroy
```

## ✨ **PyPI Package Architecture**

### 🌟 **Zero Setup Required**
- **uvx execution**: No installation or environment setup needed
- **Python packaging**: Clean CLI with Rich output and proper error handling
- **Direct AWS deployment**: Uses boto3 for native AWS integration
- **Cross-platform**: Works on any system with Python 3.12+

### 🔥 **What This Provides**
- ✅ **Instant execution** → `uvx amauo` works immediately
- ✅ **Rich terminal UI** → Beautiful tables and progress indicators
- ✅ **Proper YAML parsing** → Clean configuration management
- ✅ **Type safety** → Full type annotations throughout
- ✅ **AWS-native** → Direct boto3 integration, no container overhead

### 🎯 **Superior Features**
- **Automatic spot preemption handling** - Cost-effective deployment
- **Built-in health monitoring** - Comprehensive node validation
- **Multi-region deployment** - Distributed across AWS regions
- **Deterministic node identity** - Consistent sensor identities
- **Secure credential management** - Never commit secrets

## 🏗️ **Architecture**

### Modern Stack
- **Python Package**: PyPI-distributed CLI with Rich output
- **AWS Integration**: Direct boto3 calls for native cloud operations
- **Bacalhau**: Distributed compute with Docker engine support
- **YAML Processing**: Proper PyYAML parsing and configuration management
- **Type Safety**: Full mypy type checking throughout

### Deployment Flow
```
uvx amauo create → Python CLI → AWS boto3 → Spot Instance Deploy → Health check
```

### Package Architecture
```
PyPI Package (amauo):
├── CLI framework with Rich UI
├── AWS Resource Manager
├── SSH Manager for remote operations
├── YAML configuration parsing
├── State management (JSON-based)
└── Node identity generation
```

## 📋 **Prerequisites**

### Required
- **Python 3.12+** (for uvx, usually already installed)
- **AWS Account** with EC2 permissions
- **AWS Credentials** configured in `~/.aws/credentials` or environment

### Automatic
The CLI automatically handles:
- **AWS resource management** (VPC, Security Groups, Key Pairs)
- **Prerequisites checking** (AWS access, SSH keys)
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
Edit `config.yaml` to customize:

```yaml
aws:
  total_instances: 3
  username: ubuntu
  ssh_key_name: my-key
  files_directory: "deployment-files"
  scripts_directory: "instance/scripts"

regions:
  - us-west-2:
      machine_type: t3.medium
      image: auto  # Auto-discovers latest Ubuntu 22.04
  - us-east-1:
      machine_type: t3.medium
      image: auto
```

## 🔧 **Commands**

### Core Operations
```bash
# Deploy instances across AWS regions
uvx amauo create

# List all running instances with details
uvx amauo list

# Destroy all instances
uvx amauo destroy

# Setup initial configuration
uvx amauo setup

# Show version
uvx amauo version

# Show help
uvx amauo help

# Migrate from legacy spot-deployer
uvx amauo migrate
```

### Advanced Options
```bash
# Custom config file
uvx amauo create -c my-config.yaml

# Show logs to console instead of log file
uvx amauo create --console

# Custom log file location
uvx amauo create --log-file deployment.log
```

## 🧪 **Local Development & Testing**

### Quick Test
```bash
# Test the CLI without installation
uvx amauo --version

# Check prerequisites
uvx amauo check

# Test with dry run (if available)
uvx amauo create --help
```

### Local Development
```bash
# Clone the repository for development
git clone <repository-url>
cd bacalhau-skypilot

# Install in development mode with uv
uv pip install -e .

# Run locally during development
python -m amauo.cli --version

# Run tests
uv run pytest

# Run linting
uv run ruff check .
```

### Debug Deployment
```bash
# Enable console logging for debugging
uvx amauo create --console

# Check SkyPilot status
uvx amauo status

# View detailed logs
uvx amauo logs

# SSH to node for debugging
uvx amauo ssh
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
# Test change
