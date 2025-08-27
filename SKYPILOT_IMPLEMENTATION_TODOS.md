# SkyPilot Implementation - Step-by-Step TODO List

## Overview
This document provides granular, sequential tasks for migrating from the current custom AWS spot deployment tool to SkyPilot. Each task is designed to be completed independently and in order.

## Phase 1: Environment Setup (Day 1)

### 1.1 Install SkyPilot
```bash
# Task: Install SkyPilot with AWS support
pip install --upgrade pip
pip install "skypilot[aws]"
```
**Verification**: Run `sky check` to confirm installation

### 1.2 Configure AWS Credentials for SkyPilot
```bash
# Task: Ensure AWS credentials are properly configured
aws configure list
sky check aws
```
**Verification**: Output should show "AWS: enabled"

### 1.3 Create Project Backup
```bash
# Task: Create a backup branch and tag
git checkout -b pre-skypilot-migration
git add .
git commit -m "Backup before SkyPilot migration"
git tag pre-skypilot-backup
```
**Verification**: `git tag -l` shows the backup tag

### 1.4 Create New Directory Structure
```bash
# Task: Create SkyPilot directories
mkdir -p skypilot-tasks
mkdir -p sky-cli
mkdir -p deployment-new/etc/bacalhau
mkdir -p deployment-new/opt/bacalhau
mkdir -p deployment-new/opt/sensor/config
mkdir -p deployment-new/scripts
```
**Verification**: `tree skypilot-tasks deployment-new` shows structure

## Phase 2: Basic SkyPilot Task Creation (Day 2)

### 2.1 Create Minimal SkyPilot Task
```yaml
# Task: Create skypilot-tasks/test-minimal.yaml
name: bacalhau-test-minimal

resources:
  cloud: aws
  region: us-west-2
  instance_type: t3.small
  use_spot: true

run: |
  echo "SkyPilot node is running!"
  uname -a
  docker --version || echo "Docker not installed"
```
**Verification**: `sky launch skypilot-tasks/test-minimal.yaml --down`

### 2.2 Test File Mounting
```yaml
# Task: Create skypilot-tasks/test-file-mount.yaml
name: bacalhau-test-files

resources:
  cloud: aws
  instance_type: t3.small
  use_spot: true

file_mounts:
  /tmp/test-file.txt: ./README.md

run: |
  ls -la /tmp/
  cat /tmp/test-file.txt | head -5
```
**Verification**: File appears on remote node

### 2.3 Test Docker Installation
```yaml
# Task: Create skypilot-tasks/test-docker.yaml
name: bacalhau-test-docker

resources:
  cloud: aws
  instance_type: t3.small
  use_spot: true

setup: |
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker $USER

run: |
  sudo docker run hello-world
  sudo docker ps -a
```
**Verification**: Docker hello-world runs successfully

## Phase 3: Port Docker Compose Files (Day 3)

### 3.1 Copy Docker Compose Files to New Structure
```bash
# Task: Copy existing Docker Compose files
cp deployment/opt/bacalhau/docker-compose.yml deployment-new/opt/bacalhau/
cp deployment/opt/sensor/docker-compose.yml deployment-new/opt/sensor/
```
**Verification**: Files exist in deployment-new

### 3.2 Create Bacalhau Config Generator Script
```python
# Task: Create deployment-new/scripts/generate_bacalhau_config.py
#!/usr/bin/env python3
import os
import yaml
import sys

def generate_config():
    # Read orchestrator credentials
    endpoint_file = '/etc/bacalhau/orchestrator_endpoint'
    token_file = '/etc/bacalhau/orchestrator_token'

    if not os.path.exists(endpoint_file):
        print("Warning: orchestrator_endpoint file not found")
        return False

    with open(endpoint_file, 'r') as f:
        endpoint = f.read().strip()

    token = ""
    if os.path.exists(token_file):
        with open(token_file, 'r') as f:
            token = f.read().strip()

    # Generate config
    config = {
        'node': {
            'type': 'compute',
            'orchestrator': {
                'endpoint': endpoint,
                'token': token
            },
            'compute': {
                'enabled': True,
                'engines': {
                    'docker': {'enabled': True}
                }
            }
        }
    }

    # Write config
    with open('/etc/bacalhau/config.yaml', 'w') as f:
        yaml.dump(config, f)

    print("Generated /etc/bacalhau/config.yaml")
    return True

if __name__ == '__main__':
    sys.exit(0 if generate_config() else 1)
```
**Verification**: Script runs without errors locally

### 3.3 Port Node Identity Generator
```bash
# Task: Copy and adapt node identity generator
cp instance/scripts/generate_node_identity.py deployment-new/opt/sensor/
# Update paths in the script to work with new structure
```
**Verification**: Script generates valid JSON when INSTANCE_ID is set

## Phase 4: Create Main SkyPilot Task (Day 4)

### 4.1 Create Orchestrator Credential Files
```bash
# Task: Create credential files (DO NOT COMMIT)
echo "nats://your-orchestrator.example.com:4222" > deployment-new/etc/bacalhau/orchestrator_endpoint
echo "your-secret-token-here" > deployment-new/etc/bacalhau/orchestrator_token
# Add to .gitignore
echo "deployment-new/etc/bacalhau/orchestrator_*" >> .gitignore
```
**Verification**: Files exist but are gitignored

### 4.2 Create Main Deployment Task
```yaml
# Task: Create skypilot-tasks/bacalhau-node.yaml
name: bacalhau-sensor-node

resources:
  cloud: aws
  region: us-west-2
  instance_type: t3.medium
  use_spot: true
  disk_size: 30

file_mounts:
  # Bacalhau files
  /tmp/deploy/etc/bacalhau/orchestrator_endpoint: ./deployment-new/etc/bacalhau/orchestrator_endpoint
  /tmp/deploy/etc/bacalhau/orchestrator_token: ./deployment-new/etc/bacalhau/orchestrator_token
  /tmp/deploy/opt/bacalhau/docker-compose.yml: ./deployment-new/opt/bacalhau/docker-compose.yml

  # Sensor files
  /tmp/deploy/opt/sensor/docker-compose.yml: ./deployment-new/opt/sensor/docker-compose.yml
  /tmp/deploy/opt/sensor/config/sensor-config.yaml: ./deployment-new/opt/sensor/config/sensor-config.yaml
  /tmp/deploy/opt/sensor/generate_node_identity.py: ./deployment-new/opt/sensor/generate_node_identity.py

  # Scripts
  /tmp/deploy/scripts/generate_bacalhau_config.py: ./deployment-new/scripts/generate_bacalhau_config.py

setup: |
  # Install dependencies
  sudo apt-get update
  sudo apt-get install -y python3 python3-pip ec2-metadata

  # Install Docker
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker $USER

  # Install Docker Compose
  sudo apt-get install -y docker-compose-plugin

  # Create directories
  sudo mkdir -p /etc/bacalhau /opt/bacalhau /opt/sensor/config /opt/sensor/data

  # Copy files from staging
  sudo cp /tmp/deploy/etc/bacalhau/* /etc/bacalhau/
  sudo cp /tmp/deploy/opt/bacalhau/* /opt/bacalhau/
  sudo cp -r /tmp/deploy/opt/sensor/* /opt/sensor/
  sudo cp /tmp/deploy/scripts/* /usr/local/bin/
  sudo chmod +x /usr/local/bin/*.py

  # Generate Bacalhau config
  sudo python3 /usr/local/bin/generate_bacalhau_config.py

  # Generate node identity
  cd /opt/sensor
  INSTANCE_ID=$(ec2-metadata --instance-id | cut -d ' ' -f 2)
  sudo INSTANCE_ID=$INSTANCE_ID python3 generate_node_identity.py

run: |
  # Start services
  cd /opt/bacalhau && sudo docker compose up -d
  cd /opt/sensor && sudo docker compose up -d

  # Wait and verify
  sleep 10
  sudo docker ps
  echo "Deployment complete!"
```
**Verification**: Services start successfully

## Phase 5: Multi-Node Deployment (Day 5)

### 5.1 Create Multi-Node Configuration
```yaml
# Task: Update bacalhau-node.yaml with num_nodes
resources:
  cloud: aws
  region: us-west-2
  instance_type: t3.medium
  use_spot: true
  disk_size: 30
  num_nodes: 3  # Add this line
```
**Verification**: `sky launch` creates 3 nodes

### 5.2 Test Node Communication
```yaml
# Task: Add node discovery test to run section
run: |
  # ... existing commands ...

  # Test node discovery
  sudo docker exec $(sudo docker ps -q -f name=compute) \
    bacalhau node list
```
**Verification**: Nodes see each other

## Phase 6: CLI Wrapper (Day 6)

### 6.1 Create Basic CLI Wrapper
```bash
# Task: Create sky-cli/sky-deploy
#!/bin/bash
set -e

TASK_FILE="skypilot-tasks/bacalhau-node.yaml"
CLUSTER_NAME="bacalhau-cluster"

case "$1" in
  create)
    sky launch -c $CLUSTER_NAME $TASK_FILE
    ;;
  list)
    sky status $CLUSTER_NAME
    ;;
  destroy)
    sky down $CLUSTER_NAME -y
    ;;
  ssh)
    sky ssh $CLUSTER_NAME
    ;;
  logs)
    sky exec $CLUSTER_NAME "sudo docker logs bacalhau_compute_1"
    ;;
  *)
    echo "Usage: $0 {create|list|destroy|ssh|logs}"
    exit 1
    ;;
esac
```
**Verification**: Each command works

### 6.2 Add Configuration Support
```bash
# Task: Update CLI to read config.yaml
# Add logic to read instance count, regions, etc. from config.yaml
# Use yq or python to parse YAML
```
**Verification**: CLI respects configuration

## Phase 7: AWS Credentials & S3 Support (Day 7)

### 7.1 Add AWS Credentials to Deployment
```yaml
# Task: Add to file_mounts in bacalhau-node.yaml
file_mounts:
  # ... existing mounts ...
  /tmp/deploy/etc/aws/credentials: ./deployment-new/etc/aws/credentials

# Add to setup:
setup: |
  # ... existing setup ...
  sudo mkdir -p /root/.aws
  sudo cp /tmp/deploy/etc/aws/credentials /root/.aws/
  sudo chmod 600 /root/.aws/credentials
```
**Verification**: S3 access works from containers

### 7.2 Test S3 Integration
```bash
# Task: Add S3 test to health check
sky exec bacalhau-cluster "sudo docker exec \$(sudo docker ps -q -f name=sensor) aws s3 ls"
```
**Verification**: S3 buckets are listed

## Phase 8: Health Checks & Monitoring (Day 8)

### 8.1 Create Health Check Script
```bash
# Task: Create deployment-new/scripts/health-check.sh
#!/bin/bash
echo "=== Health Check ==="
echo "Docker Status:"
sudo docker ps

echo -e "\nBacalhau Status:"
sudo docker exec $(sudo docker ps -q -f name=compute) bacalhau version

echo -e "\nSensor Status:"
sudo docker logs --tail 10 $(sudo docker ps -q -f name=sensor)

echo -e "\nDisk Usage:"
df -h /

echo -e "\nMemory Usage:"
free -h
```
**Verification**: Script provides useful output

### 8.2 Add Automated Health Monitoring
```yaml
# Task: Add to run section of bacalhau-node.yaml
run: |
  # ... existing run commands ...

  # Setup recurring health check
  (crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/health-check.sh > /var/log/health-check.log 2>&1") | crontab -
```
**Verification**: Health checks run every 5 minutes

## Phase 9: Testing & Validation (Day 9)

### 9.1 Single Node Test
```bash
# Task: Deploy single node and validate
./sky-cli/sky-deploy create
sleep 120
./sky-cli/sky-deploy logs
./sky-cli/sky-deploy destroy
```
**Verification**: All services healthy

### 9.2 Multi-Node Test
```bash
# Task: Test 3-node deployment
# Update config for 3 nodes
./sky-cli/sky-deploy create
# Verify all nodes join cluster
./sky-cli/sky-deploy destroy
```
**Verification**: All nodes communicate

### 9.3 Spot Preemption Test
```bash
# Task: Test spot recovery
# Deploy cluster
# Simulate preemption (or wait for one)
# Verify automatic recovery
```
**Verification**: Cluster recovers from preemption

## Phase 10: Documentation & Cleanup (Day 10)

### 10.1 Update README
```markdown
# Task: Update README.md with new instructions
## Quick Start with SkyPilot
1. Install: `pip install "skypilot[aws]"`
2. Configure: `sky check`
3. Deploy: `./sky-cli/sky-deploy create`
4. Monitor: `./sky-cli/sky-deploy list`
5. Destroy: `./sky-cli/sky-deploy destroy`
```
**Verification**: Documentation is clear

### 10.2 Create Migration Guide
```markdown
# Task: Create MIGRATION_FROM_LEGACY.md
## For Existing Users
1. Backup your config.yaml
2. Install SkyPilot
3. Copy credentials to deployment-new/
4. Run new deployment
```
**Verification**: Guide covers all scenarios

### 10.3 Archive Legacy Code
```bash
# Task: Move old code to legacy/
mkdir -p legacy
mv spot_deployer legacy/
mv deploy_spot.py legacy/
git add -A
git commit -m "Archive legacy deployment code"
```
**Verification**: Old code preserved but moved

### 10.4 Final Testing
```bash
# Task: Complete end-to-end test
# Clean environment test
# Deploy full cluster
# Run workload
# Verify outputs
# Clean teardown
```
**Verification**: Everything works as expected

## Success Criteria

After completing all tasks:
- [ ] SkyPilot deploys nodes successfully
- [ ] Bacalhau nodes connect to orchestrator
- [ ] Sensor service generates data
- [ ] S3 access works
- [ ] Multi-node clusters work
- [ ] Spot preemption recovery works
- [ ] Documentation is complete
- [ ] Legacy code is archived
- [ ] CI/CD updated (if applicable)
- [ ] Team trained on new system

## Notes for Implementation

1. **Execute tasks sequentially** - Each task builds on previous ones
2. **Test after each phase** - Don't proceed if something is broken
3. **Keep credentials secure** - Never commit secrets
4. **Document issues** - Keep notes of any problems encountered
5. **Create rollback plan** - Be ready to revert if needed

## Support Resources

- SkyPilot Docs: https://docs.skypilot.co/
- SkyPilot GitHub: https://github.com/skypilot-org/skypilot
- SkyPilot Slack: Join for community support
- Our Migration Plan: SKYPILOT_MIGRATION_PLAN.md
