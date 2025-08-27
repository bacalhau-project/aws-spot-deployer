# SkyPilot Bacalhau Deployment

Modern, cloud-agnostic deployment of Bacalhau compute nodes with sensor simulators using SkyPilot.

## Overview

This deployment system replaces the legacy custom AWS deployment tool with SkyPilot, providing:

- **Multi-cloud support**: AWS (others coming soon)
- **Spot instance management**: Automatic recovery from preemptions
- **Clean architecture**: No backward compatibility baggage
- **Simple operations**: Single CLI for all deployment tasks
- **Robust health monitoring**: Built-in health checks and status reporting

## Quick Start

### 1. Setup

```bash
# Run initial setup
./setup-example.sh

# Edit credential files (REQUIRED)
nano credentials/orchestrator_endpoint
nano credentials/orchestrator_token
nano credentials/aws-credentials
```

### 2. Deploy

```bash
# Deploy 6 nodes across 3 regions
./sky-deploy deploy
```

### 3. Monitor

```bash
# Check cluster status
./sky-deploy status

# View node health
./sky-deploy logs

# SSH to nodes
./sky-deploy ssh
```

### 4. Cleanup

```bash
# Destroy cluster (when done)
./sky-deploy destroy
```

## Architecture

### Components

- **SkyPilot**: Cloud orchestration and spot instance management
- **Bacalhau**: Distributed compute nodes with Docker engine support
- **Sensor Simulator**: Generates realistic IoT sensor data
- **Health Monitoring**: Automated health checks and status reporting

### File Structure

```
skypilot-deployment/
├── sky-config.yaml              # Deployment configuration
├── bacalhau-cluster.yaml        # SkyPilot task definition
├── sky-deploy                   # CLI wrapper
├── install_skypilot.py         # SkyPilot installer/validator
├── setup-example.sh            # Environment setup
├── credentials/                 # Credential files (not in git)
│   ├── orchestrator_endpoint
│   ├── orchestrator_token
│   └── aws-credentials
├── config/                      # Configuration files
│   └── sensor-config.yaml
├── compose/                     # Docker Compose files
│   ├── bacalhau-compose.yml
│   └── sensor-compose.yml
└── scripts/                     # Deployment scripts
    ├── generate_bacalhau_config.py
    ├── generate_node_identity.py
    └── health_check.sh
```

## Configuration

### Deployment Settings (sky-config.yaml)

```yaml
deployment:
  name: "bacalhau-sensors"
  total_nodes: 6

  node:
    instance_type: "t3.medium"
    use_spot: true
    disk_size: 30

  regions:
    - "us-west-2"
    - "us-east-1"
    - "eu-west-1"

  network:
    public_ip: true
    ingress_ports: [22, 4222, 1234]
```

### Required Credentials

#### credentials/orchestrator_endpoint
```
nats://your-orchestrator.example.com:4222
```

#### credentials/orchestrator_token
```
your-secret-token-here
```

#### credentials/aws-credentials
```
[default]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
region = us-west-2
```

## Features

### Multi-Cloud Node Identity

The system generates deterministic node identities that work across cloud providers:

```json
{
  "node_id": "i-1234567890abcdef0",
  "location": {
    "city": "San Francisco",
    "state": "CA",
    "coordinates": {"latitude": 37.7749, "longitude": -122.4194}
  },
  "sensor": {
    "manufacturer": "Honeywell",
    "model": "BME280",
    "serial_number": "HO1234567"
  },
  "metadata": {
    "cloud_provider": "aws",
    "region": "us-west-2"
  }
}
```

### Automatic Health Monitoring

Built-in health checks validate:
- Docker service status
- Container health (Bacalhau + Sensor)
- Network connectivity (API ports)
- File system status
- Resource utilization
- Orchestrator connectivity
- Log analysis for errors

### Spot Instance Resilience

SkyPilot automatically:
- Handles spot instance preemptions
- Retries failed deployments
- Distributes load across regions
- Maintains desired node count

## CLI Commands

| Command | Description |
|---------|-------------|
| `./sky-deploy deploy` | Deploy the cluster |
| `./sky-deploy status` | Show cluster status |
| `./sky-deploy logs` | View health status |
| `./sky-deploy logs --node N` | View specific node |
| `./sky-deploy ssh` | SSH to first node |
| `./sky-deploy ssh --node N` | SSH to specific node |
| `./sky-deploy destroy` | Destroy cluster |

## Networking

SkyPilot automatically configures:

- **Security Groups**: SSH (22), Bacalhau API (1234), NATS (4222)
- **Public IPs**: All nodes get public IPs for external access
- **VPC/Subnets**: Uses default VPC or creates as needed
- **Load Balancing**: Distributes nodes across availability zones

## Comparison to Legacy System

| Feature | Legacy | SkyPilot |
|---------|---------|----------|
| Cloud Support | AWS only | Multi-cloud |
| Spot Recovery | Manual | Automatic |
| Configuration | Complex YAML | Simple YAML |
| State Management | JSON files | SkyPilot state |
| File Transfer | Tarball+SCP | file_mounts |
| Networking | Manual setup | Automatic |
| Health Checks | Custom scripts | Built-in + custom |
| CLI | Multiple tools | Single CLI |

## Troubleshooting

### Common Issues

#### Credential Errors
```bash
# Check AWS credentials
aws sts get-caller-identity

# Verify SkyPilot
sky check aws
```

#### Deployment Failures
```bash
# Check SkyPilot logs
sky logs bacalhau-sensors

# View node health
./sky-deploy logs
```

#### Node Communication Issues
```bash
# SSH to node and check
./sky-deploy ssh
sudo docker ps
sudo docker logs bacalhau-compute
```

### Debugging

```bash
# View detailed SkyPilot status
sky status -r

# Check specific node health
./sky-deploy logs --node 1

# Run health check manually
./sky-deploy ssh --node 1
/opt/scripts/health_check.sh
```

## Development

### Testing Changes

1. Modify configuration files
2. Test with dry-run: `sky launch --dry-run bacalhau-cluster.yaml`
3. Deploy to test cluster: `./sky-deploy deploy`
4. Validate: `./sky-deploy logs`

### Adding Cloud Providers

1. Update `sky-config.yaml` cloud settings
2. Modify `generate_node_identity.py` for cloud detection
3. Test with: `sky check <provider>`

## Security

- Credential files are automatically excluded from git
- AWS credentials mounted read-only in containers
- Security groups restrict access to necessary ports only
- All communication uses standard cloud provider security

## Contributing

1. Test changes with small deployments first
2. Update documentation for any configuration changes
3. Ensure health checks validate new features
4. Follow the "no backward compatibility" principle

## Support

- SkyPilot Documentation: https://docs.skypilot.co/
- Issues: Use this repository's issue tracker
- Community: SkyPilot Slack/Discord channels
