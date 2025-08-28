# 🌍 Global Bacalhau Network - Deploy Worldwide in One Command

**Docker-powered worldwide deployment of Bacalhau compute nodes using SkyPilot.**

Deploy 9 Bacalhau compute nodes instantly across continents: US West, US East, Europe, Asia Pacific, South America, and more. Uses Docker containers for reliable deployment with zero Python environment issues.

## 🚀 **One-Command Global Deployment**

Deploy 9 nodes across worldwide zones with a single command:

```bash
# Prerequisites: Docker must be installed and running

# Deploy global cluster (9 nodes worldwide across different continents)
./cluster-deploy create

# Check status
./cluster-deploy status

# View logs
./cluster-deploy logs

# SSH to nodes
./cluster-deploy ssh

# Clean up
./cluster-deploy destroy
```

## ✨ **Docker-First Architecture**

### 🌟 **Zero Environment Issues**
- **Docker containers**: No Python/UV installation required
- **Pre-built SkyPilot image**: `berkeleyskypilot/skypilot` with everything included
- **Volume mounts**: AWS credentials and workspace automatically mounted
- **Automatic container management**: Handles container lifecycle

### 🔥 **What This Eliminates**
- ❌ **Python version conflicts** → Docker container has correct Python
- ❌ **Virtual environment issues** → Container provides isolated environment
- ❌ **Package installation failures** → SkyPilot pre-installed in container
- ❌ **UV/pip wheel build errors** → No local package installation needed
- ❌ **Platform-specific issues** → Container works everywhere Docker runs

### 🎯 **Superior Features**
- **Automatic spot preemption recovery** - Never lose your cluster
- **Built-in health monitoring** - Comprehensive node validation
- **Multi-region deployment** - Distributed across availability zones
- **Cloud-agnostic node identity** - Works on AWS, GCP, Azure
- **Secure credential management** - Never commit secrets

## 🏗️ **Architecture**

### Modern Stack
- **Docker**: Containerized SkyPilot environment
- **SkyPilot**: Cloud orchestration and spot management
- **Bacalhau**: Distributed compute with Docker engine support
- **Sensor Simulator**: Realistic IoT data generation
- **Docker Compose**: Service orchestration on nodes

### Deployment Flow
```
./cluster-deploy create → Docker container → SkyPilot deploy → Health check
```

### Container Architecture
```
Host Machine:
├── cluster-deploy (bash script)
├── cluster.yaml (SkyPilot config)
├── credentials/ (mounted into container)
└── Docker Container:
    ├── berkeleyskypilot/skypilot image
    ├── Volume mounts: ~/.aws, ~/.sky, workspace
    └── SkyPilot manages: EC2, file sync, deployment
```

## 📋 **Prerequisites**

### Required
- **Docker** installed and running (`docker --version`)
- **AWS Account** with EC2 permissions
- **AWS Credentials** configured in `~/.aws/credentials` or environment

### Automatic
The script automatically handles:
- **SkyPilot Docker image** pull and management
- **Container lifecycle** (start, stop, cleanup)
- **Volume mounting** (AWS creds, workspace, SkyPilot state)
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
# Deploy 9-node cluster across global regions
./cluster-deploy create

# Check cluster status and health
./cluster-deploy status

# View deployment logs
./cluster-deploy logs

# SSH to cluster head node
./cluster-deploy ssh

# Destroy entire cluster
./cluster-deploy destroy

# Stop Docker container (cleanup)
./cluster-deploy cleanup

# Show help
./cluster-deploy help
```

### Advanced Options
```bash
# Custom config file
./cluster-deploy create -c my-config.yaml

# Custom cluster name
./cluster-deploy create -n my-cluster

# Deploy with specific config and name
./cluster-deploy create -c production.yaml -n prod-cluster
```

## 🧪 **Local Development & Testing**

### Quick Test
```bash
# Clone the repository
git clone <repository-url>
cd bacalhau-skypilot

# Ensure Docker is running
docker --version

# Test prerequisites check
./cluster-deploy help

# Check if SkyPilot container works
./cluster-deploy status
```

### Debug Deployment
```bash
# Run with bash debugging
bash -x ./cluster-deploy create

# Check Docker container directly
docker exec skypilot-cluster-deploy sky status

# View SkyPilot logs through container
docker exec skypilot-cluster-deploy sky logs <cluster-name>

# SSH to node through container
docker exec -it skypilot-cluster-deploy sky ssh <cluster-name>
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
