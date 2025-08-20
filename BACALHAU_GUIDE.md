# Bacalhau Compute Cluster Guide

This guide explains how the default Bacalhau deployment works and how to use your compute cluster.

## Overview

Every instance deployed by spot-deployer automatically becomes a Bacalhau compute node that:
- Connects to the orchestrator at **147.135.16.87**
- Joins the cluster with authentication token
- Runs jobs submitted to the cluster
- Supports Docker and WASM workloads

## Architecture

```
┌─────────────────┐
│   Orchestrator  │
│  147.135.16.87  │
│   (External)    │
└────────┬────────┘
         │ NATS
         │ Port 4222
    ┌────┴────┐
    │         │
┌───▼──┐  ┌──▼───┐
│Node 1│  │Node 2│  ...  Your Spot Instances
│Docker│  │Docker│       (Compute Nodes)
└──────┘  └──────┘
```

## Configuration

The Bacalhau configuration is located in `.spot/configs/bacalhau-config.yaml`:

```yaml
API:
  Host: 147.135.16.87
  Port: 1234
  TLS:
    UseTLS: true
    Insecure: false

Compute:
  Enabled: true
  Orchestrators:
    - nats://147.135.16.87:4222
  Auth:
    Token: 9847fc83-f353-4cf6-8001-b82da00bacf5
```

## Verifying Your Nodes

After deployment, verify your nodes are connected:

### 1. Check Service Status

SSH into any instance:
```bash
ssh ubuntu@<instance-ip>

# Check Docker Compose status
cd /opt/bacalhau
docker compose ps

# View logs
docker compose logs -f
```

### 2. Check Node Health

```bash
# Inside the container
docker compose exec compute bacalhau version
docker compose exec compute bacalhau node list
```

### 3. Verify Cluster Connection

The logs should show:
```
INFO Connected to orchestrator at nats://147.135.16.87:4222
INFO Node registered successfully
INFO Ready to accept jobs
```

## Submitting Jobs

You can submit jobs to the cluster from any machine with Bacalhau CLI:

### Install Bacalhau CLI

```bash
curl -sL https://get.bacalhau.org/install.sh | bash
```

### Configure CLI

```bash
export BACALHAU_API_HOST=147.135.16.87
export BACALHAU_API_PORT=1234
```

### Submit a Test Job

```bash
# Run a simple Docker job
bacalhau docker run ubuntu echo "Hello from Bacalhau"

# Check job status
bacalhau job describe <job-id>

# Get job results
bacalhau job get <job-id>
```

## Example Jobs

### 1. Data Processing Job

```bash
bacalhau docker run \
  -i ipfs://QmExample:/data \
  python:3.9 \
  python -c "import os; print(os.listdir('/data'))"
```

### 2. Machine Learning Job

```bash
bacalhau docker run \
  --gpu 1 \
  tensorflow/tensorflow:latest-gpu \
  python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

### 3. WASM Job

```bash
bacalhau wasm run \
  --entry-point=_start \
  program.wasm
```

## Monitoring

### View Node Metrics

```bash
# On the compute node
docker compose exec compute bacalhau node describe $(bacalhau node id)
```

### Check Resource Usage

```bash
# Docker stats
docker stats bacalhau-compute-compute-1

# System resources
htop
df -h
```

### View Jobs Running on Node

```bash
docker compose exec compute bacalhau job list --node-id $(bacalhau node id)
```

## Troubleshooting

### Node Not Connecting

1. **Check network connectivity**:
   ```bash
   nc -zv 147.135.16.87 4222
   ```

2. **Verify configuration**:
   ```bash
   cat /opt/bacalhau/config.yaml
   ```

3. **Check Docker logs**:
   ```bash
   docker compose logs compute --tail=100
   ```

### Jobs Not Running

1. **Check node capacity**:
   ```bash
   docker compose exec compute bacalhau node describe $(bacalhau node id)
   ```

2. **Verify Docker is accessible**:
   ```bash
   docker ps
   ls -la /var/run/docker.sock
   ```

### Service Won't Start

1. **Check service status**:
   ```bash
   sudo systemctl status bacalhau
   sudo journalctl -u bacalhau -f
   ```

2. **Restart service**:
   ```bash
   sudo systemctl restart bacalhau
   ```

## Scaling

### Add More Nodes

Simply deploy more instances:
```bash
# Edit config.yaml to increase instance count
spot create
```

### Remove Nodes

Nodes can be safely removed:
```bash
spot destroy
```

The cluster will automatically rebalance jobs.

## Security Considerations

1. **Authentication Token**: The token `9847fc83-f353-4cf6-8001-b82da00bacf5` authenticates nodes
2. **TLS Encryption**: All API communications use TLS
3. **Network Security**: Ensure security groups allow port 4222 for NATS
4. **Docker Socket**: The container has access to Docker socket for running jobs

## Advanced Configuration

### Custom Resource Limits

Edit `.spot/configs/bacalhau-config.yaml`:
```yaml
Compute:
  Resources:
    CPU: "4"        # Limit to 4 CPUs
    Memory: "8Gi"   # Limit to 8GB RAM
    Disk: "100Gi"   # Limit to 100GB disk
```

### Enable GPU Support

If using GPU instances:
```yaml
Compute:
  Resources:
    GPU: "1"  # Number of GPUs to expose
```

### Change Node Labels

Add labels for job targeting:
```yaml
Compute:
  Labels:
    region: us-west-2
    type: gpu
    tier: premium
```

## Resources

- [Bacalhau Documentation](https://docs.bacalhau.org)
- [API Reference](https://docs.bacalhau.org/api)
- [Example Jobs](https://github.com/bacalhau-project/examples)
- [CLI Guide](https://docs.bacalhau.org/cli)