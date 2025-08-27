# SkyPilot Migration Plan - Ultrathink Architecture Analysis

## Executive Summary

This document outlines a comprehensive plan to migrate the current custom AWS spot instance deployment tool to SkyPilot, a modern cloud orchestration framework. The goal is to maintain the existing Docker Compose-based service architecture while leveraging SkyPilot's superior cloud abstraction, spot instance management, and file synchronization capabilities.

## 1. Current Architecture Analysis

### Core Components
- **Custom Python Package** (`spot_deployer/`): Manages AWS spot instances directly via boto3
- **Docker Compose Services**:
  - Bacalhau compute node container
  - Sensor simulator container
- **File Distribution**: Tarball-based deployment with SSH transfers
- **Node Identity**: Deterministic generation based on EC2 instance ID
- **State Management**: JSON-based instance tracking
- **Credentials**: Orchestrator endpoint and token files

### Deployment Flow
1. Create spot instances using boto3
2. Wait for SSH availability
3. Create and upload deployment tarball
4. Extract files to proper locations
5. Run setup.sh to configure services
6. Start Docker Compose services via SystemD
7. Generate node identity for sensor

### Key Files and Locations
```
/etc/bacalhau/config.yaml           # Bacalhau configuration
/opt/bacalhau/docker-compose.yml    # Bacalhau service
/opt/sensor/docker-compose.yml      # Sensor service
/opt/sensor/config/                 # Sensor configuration
/root/.aws/credentials               # AWS credentials for S3
```

## 2. SkyPilot Capabilities Assessment

### Strengths for Our Use Case
- **Native Spot Instance Support**: Built-in spot management with automatic recovery
- **File Synchronization**: Robust `file_mounts` and `workdir` syncing
- **Docker Support**: First-class Docker container deployment
- **Multi-Cloud**: Future-proof with support for 17+ cloud providers
- **Cost Optimization**: Automatic cheapest zone/region selection
- **Environment Variables**: Secure handling of secrets and credentials
- **Setup/Run Separation**: Clear lifecycle management

### Migration Advantages
- Eliminate custom AWS management code (~2000 lines)
- Automatic spot instance recovery from preemptions
- Built-in retry logic and error handling
- Simplified cluster lifecycle management
- Better observability and debugging

## 3. New Architecture Design

### SkyPilot Task YAML Structure
```yaml
name: bacalhau-sensor-cluster

resources:
  cloud: aws
  instance_type: t3.medium
  use_spot: true
  disk_size: 50
  num_nodes: 3

workdir: ./deployment

file_mounts:
  # Bacalhau orchestrator credentials
  /etc/bacalhau/orchestrator_endpoint: ./deployment/etc/bacalhau/orchestrator_endpoint
  /etc/bacalhau/orchestrator_token: ./deployment/etc/bacalhau/orchestrator_token

  # Docker Compose files
  /opt/bacalhau/docker-compose.yml: ./deployment/opt/bacalhau/docker-compose.yml
  /opt/sensor/docker-compose.yml: ./deployment/opt/sensor/docker-compose.yml

  # Sensor configuration
  /opt/sensor/config/sensor-config.yaml: ./deployment/opt/sensor/config/sensor-config.yaml

  # AWS credentials for S3 access
  /root/.aws/credentials: ./deployment/etc/aws/credentials

  # Scripts
  /opt/sensor/generate_node_identity.py: ./deployment/opt/sensor/generate_node_identity.py

envs:
  BACALHAU_ORCHESTRATOR_ENDPOINT_FILE: /etc/bacalhau/orchestrator_endpoint
  BACALHAU_ORCHESTRATOR_TOKEN_FILE: /etc/bacalhau/orchestrator_token

setup: |
  # Install Docker
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker $USER

  # Install Docker Compose plugin
  sudo apt-get update
  sudo apt-get install -y docker-compose-plugin python3 python3-pip

  # Create directories
  sudo mkdir -p /etc/bacalhau /var/log/bacalhau /opt/sensor/data /opt/sensor/exports

  # Generate Bacalhau config from credentials
  sudo python3 /opt/generate_bacalhau_config.py

  # Generate node identity
  cd /opt/sensor
  INSTANCE_ID=$(ec2-metadata --instance-id | cut -d ' ' -f 2)
  sudo INSTANCE_ID=$INSTANCE_ID python3 generate_node_identity.py

  # Set permissions
  sudo chmod 600 /root/.aws/credentials
  sudo chown -R ubuntu:ubuntu /opt/bacalhau /opt/sensor

run: |
  # Start Bacalhau compute node
  cd /opt/bacalhau
  sudo docker compose up -d

  # Start sensor simulator
  cd /opt/sensor
  sudo docker compose up -d

  # Health check
  sleep 10
  sudo docker ps
  echo "Services started successfully"
```

### Directory Structure Reorganization
```
bacalhau-skypilot/
├── skypilot-tasks/
│   ├── bacalhau-cluster.yaml       # Main SkyPilot task
│   ├── bacalhau-dev.yaml           # Development configuration
│   └── bacalhau-prod.yaml          # Production configuration
├── deployment/                      # Files to sync to nodes
│   ├── etc/
│   │   ├── bacalhau/
│   │   │   ├── orchestrator_endpoint
│   │   │   └── orchestrator_token
│   │   └── aws/
│   │       └── credentials
│   ├── opt/
│   │   ├── bacalhau/
│   │   │   └── docker-compose.yml
│   │   ├── sensor/
│   │   │   ├── docker-compose.yml
│   │   │   ├── config/
│   │   │   │   └── sensor-config.yaml
│   │   │   └── generate_node_identity.py
│   │   └── generate_bacalhau_config.py
│   └── scripts/
│       └── health-check.sh
└── sky-cli/                         # New CLI wrapper for SkyPilot
    └── sky-deploy.sh
```

## 4. Migration Strategy

### Phase 1: Foundation (Week 1)
1. Install and configure SkyPilot locally
2. Create basic SkyPilot task YAML
3. Test single-node deployment
4. Verify file mounting works correctly

### Phase 2: Service Integration (Week 2)
1. Port Docker Compose configurations
2. Implement credential management via file_mounts
3. Create Bacalhau config generator script
4. Test multi-node deployment

### Phase 3: Feature Parity (Week 3)
1. Implement node identity generation
2. Add AWS S3 credential handling
3. Create health check scripts
4. Implement cluster management CLI wrapper

### Phase 4: Testing & Refinement (Week 4)
1. End-to-end testing with real Bacalhau orchestrator
2. Performance optimization
3. Documentation update
4. Migration guide for users

## 5. Comprehensive TODO List for Implementation

### Prerequisites
- [ ] Install SkyPilot: `pip install "skypilot[aws]"`
- [ ] Configure AWS credentials for SkyPilot
- [ ] Create project backup before migration

### Core Migration Tasks

#### 1. Project Structure Setup
- [ ] Create `skypilot-tasks/` directory
- [ ] Reorganize `deployment/` directory for SkyPilot compatibility
- [ ] Move Docker Compose files to new structure
- [ ] Create `.gitignore` entries for credentials

#### 2. SkyPilot Task Configuration
- [ ] Create base `bacalhau-cluster.yaml` task file
- [ ] Define resource requirements (instance type, spot, disk)
- [ ] Configure file_mounts for all required files
- [ ] Set up environment variables
- [ ] Write setup commands for dependencies
- [ ] Write run commands for services

#### 3. Credential Management
- [ ] Create `generate_bacalhau_config.py` script
  - [ ] Read orchestrator endpoint file
  - [ ] Read orchestrator token file
  - [ ] Generate `/etc/bacalhau/config.yaml`
  - [ ] Handle missing credentials gracefully
- [ ] Update credential file documentation
- [ ] Create credential validation script

#### 4. Docker Compose Adaptation
- [ ] Review and update Bacalhau docker-compose.yml
  - [ ] Remove host networking if possible
  - [ ] Update volume mounts for SkyPilot paths
  - [ ] Add health checks
- [ ] Review and update sensor docker-compose.yml
  - [ ] Update node identity path
  - [ ] Verify AWS credential mounts
  - [ ] Add restart policies

#### 5. Node Identity System
- [ ] Port `generate_node_identity.py` to work with SkyPilot
  - [ ] Ensure EC2 metadata access works
  - [ ] Update file paths
  - [ ] Add error handling for non-AWS clouds
- [ ] Create fallback for non-EC2 environments
- [ ] Test deterministic generation

#### 6. CLI Wrapper Development
- [ ] Create `sky-deploy.sh` wrapper script
  - [ ] `create` - Launch cluster with SkyPilot
  - [ ] `list` - Show cluster status
  - [ ] `destroy` - Tear down cluster
  - [ ] `logs` - View service logs
  - [ ] `ssh` - Connect to nodes
  - [ ] `exec` - Run commands on cluster
- [ ] Add configuration file support
- [ ] Implement dry-run mode

#### 7. Multi-Node Support
- [ ] Configure `num_nodes` parameter
- [ ] Test node discovery for Bacalhau
- [ ] Implement node labeling/tagging
- [ ] Create node-specific configurations

#### 8. Monitoring and Health Checks
- [ ] Create health check script
  - [ ] Verify Docker services running
  - [ ] Check Bacalhau connectivity
  - [ ] Validate sensor data generation
- [ ] Implement status reporting
- [ ] Add automatic recovery logic

#### 9. Testing Suite
- [ ] Unit tests for configuration generator
- [ ] Integration test for single-node deployment
- [ ] Multi-node cluster test
- [ ] Spot instance preemption recovery test
- [ ] Credential rotation test
- [ ] Cross-region deployment test

#### 10. Documentation
- [ ] Update README.md with SkyPilot instructions
- [ ] Create MIGRATION_GUIDE.md for existing users
- [ ] Document new CLI commands
- [ ] Add troubleshooting section
- [ ] Create example configurations

#### 11. Advanced Features
- [ ] Add support for multiple cloud providers
- [ ] Implement auto-scaling based on load
- [ ] Create deployment templates for different scenarios
- [ ] Add cost tracking and reporting
- [ ] Implement blue-green deployments

#### 12. Cleanup and Optimization
- [ ] Remove old `spot_deployer/` package
- [ ] Archive legacy deployment scripts
- [ ] Optimize Docker images for faster pulls
- [ ] Implement caching for frequently used files
- [ ] Profile and optimize startup time

### Post-Migration Tasks
- [ ] Conduct user acceptance testing
- [ ] Create rollback plan
- [ ] Schedule gradual migration for production
- [ ] Monitor for issues in first week
- [ ] Gather feedback and iterate

## 6. Risk Assessment and Mitigation

### Risks
1. **SkyPilot Learning Curve**: New tool for team
   - Mitigation: Create comprehensive examples and documentation

2. **Credential Management Changes**: Different approach to secrets
   - Mitigation: Maintain backward compatibility during transition

3. **Multi-Cloud Complexity**: SkyPilot supports many clouds
   - Mitigation: Focus on AWS initially, expand later

4. **Docker Compose Compatibility**: Potential issues with compose v2
   - Mitigation: Test thoroughly, use docker-compose-plugin

## 7. Success Metrics

- Deployment time reduced by >50%
- Zero custom AWS management code
- Automatic recovery from spot preemptions
- Support for 3+ cloud providers
- Improved developer experience
- Reduced operational complexity

## 8. Timeline

- **Week 1**: Foundation and basic deployment
- **Week 2**: Service integration and testing
- **Week 3**: Feature completion and documentation
- **Week 4**: Testing, optimization, and rollout

## Conclusion

Migrating to SkyPilot will significantly simplify our deployment architecture while adding robust cloud abstraction, automatic spot recovery, and multi-cloud support. The migration plan outlined above provides a structured approach to achieve feature parity while improving operational efficiency and developer experience.
