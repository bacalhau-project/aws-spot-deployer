# Portable Deployment Guide

This guide explains how to use the new portable deployment features in spot-deployer.

## Quick Start

### 1. Generate a Deployment Structure

```bash
# Generate a standard .spot/ deployment structure
./spot-dev generate

# This creates:
# .spot/
#   ├── deployment.yaml   # Deployment manifest
#   ├── scripts/         # Setup scripts
#   ├── services/        # SystemD services
#   ├── configs/         # Configuration files
#   └── files/           # Additional files
```

### 2. Configure Your Deployment

Edit `.spot/deployment.yaml`:

```yaml
version: 1
packages:
  - curl
  - wget
  - git
  - python3

scripts:
  - name: setup
    path: scripts/setup.sh
    order: 1

services:
  - webapp.service

uploads:
  - source: configs/app.config
    destination: /opt/app/config.yaml
    permissions: "644"
```

### 3. Validate Configuration

```bash
# Check your deployment before running
./spot-dev validate
```

### 4. Deploy

```bash
# Deploy to AWS
./spot-dev create
```

## Deployment Types

### 1. Portable Deployments (.spot directory)

The recommended approach. Keep deployment configuration with your project:

```
your-project/
├── .spot/
│   ├── deployment.yaml
│   ├── scripts/
│   ├── services/
│   └── files/
├── src/
└── README.md
```

### 2. Convention-based Deployments

Legacy support for `deployment/` directory at project root.

### 3. Tarball Deployments

Deploy by automatically creating tarballs from local directories:

```yaml
# In deployment.yaml
tarball_source: ./my-app  # Local directory to bundle
```

The deployer will:
1. Create a tarball from the specified directory
2. Upload it to instances
3. Extract and deploy automatically

## Deployment Manifest Schema

### Basic Structure

```yaml
version: 1  # Required

# System packages to install
packages:
  - package1
  - package2

# Scripts to run during setup
scripts:
  - name: script_name
    path: scripts/script.sh
    order: 1  # Execution order

# SystemD services to install
services:
  - service1.service
  - service2.service

# Files to upload
uploads:
  - source: local/path
    destination: /remote/path
    permissions: "644"  # Optional, default: 644

# Optional: Create tarball from local directory
tarball_source: ./application  # Directory to bundle and deploy

# Optional: Template to extend
template: minimal  # or 'docker', or custom
```

### Templates

Templates provide base configurations:

- **minimal**: Basic Ubuntu setup
- **docker**: Includes Docker and Docker Compose
- **custom**: Define your own in `templates/library/`

## File Organization

### Scripts Directory

Place setup scripts in `.spot/scripts/`:

```bash
#!/bin/bash
# .spot/scripts/setup.sh

echo "Setting up application..."
cd /opt/app
npm install
npm run build
```

### Services Directory

SystemD service files in `.spot/services/`:

```ini
# .spot/services/webapp.service
[Unit]
Description=Web Application
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/app
ExecStart=/usr/bin/node server.js
Restart=always

[Install]
WantedBy=multi-user.target
```

### Files Directory

Additional files to upload in `.spot/files/`:

- Configuration files
- SSL certificates
- Static assets
- Environment files

## Validation

Always validate before deployment:

```bash
./spot-dev validate
```

Checks:
- ✅ Deployment manifest syntax
- ✅ Referenced files exist
- ✅ AWS configuration
- ✅ SSH keys
- ⚠️ Warnings for missing documentation

## Advanced Features

### Environment Variables

Pass environment variables through config.yaml:

```yaml
aws:
  environment:
    NODE_ENV: production
    API_KEY: secret123
```

### Multi-Region Deployment

Deploy to multiple regions:

```yaml
regions:
  - us-west-2:
      instances: 3
      machine_type: t3.medium
  - eu-west-1:
      instances: 2
      machine_type: t3.small
```

### Custom Cloud-Init

Extend cloud-init with custom commands:

```yaml
# In deployment.yaml
cloud_init:
  packages:
    - htop
    - vim
  runcmd:
    - echo "Custom setup"
```

## Troubleshooting

### Check Deployment Logs

```bash
# SSH into instance
ssh ubuntu@<instance-ip>

# Check deployment log
sudo cat /opt/deployment.log

# Check service status
sudo systemctl status <service-name>
```

### Common Issues

1. **Service fails to start**
   - Check service logs: `sudo journalctl -u <service>`
   - Verify file paths in service definition
   - Check file permissions

2. **Scripts fail to execute**
   - Ensure scripts have shebang (`#!/bin/bash`)
   - Check script permissions (should be executable)
   - Review `/opt/deployment.log` for errors

3. **Files not uploaded**
   - Validate manifest: `./spot-dev validate`
   - Check source paths are relative to `.spot/`
   - Verify destination directories exist

## Migration from Legacy

### From Bacalhau-specific Deployment

1. Remove Bacalhau-specific files from `files/`
2. Create `.spot/` directory
3. Move scripts to `.spot/scripts/`
4. Create `deployment.yaml` manifest
5. Test with `validate` command

### From deployment/ Convention

1. Move `deployment/` to `.spot/`
2. Create `deployment.yaml` manifest
3. Update file references
4. Validate and deploy

## Best Practices

1. **Version Control**: Commit `.spot/` directory with your project
2. **Secrets Management**: Use environment variables or AWS Secrets Manager
3. **Testing**: Always validate before deployment
4. **Documentation**: Include README in `.spot/` directory
5. **Idempotency**: Make scripts re-runnable without side effects
6. **Logging**: Add logging to your scripts and services
7. **Health Checks**: Implement health check endpoints
8. **Monitoring**: Use CloudWatch or external monitoring

## Example Projects

### Node.js Web Application

```yaml
version: 1
template: minimal
packages:
  - nodejs
  - npm

scripts:
  - name: setup
    path: scripts/install.sh
    order: 1
  - name: configure
    path: scripts/configure.sh
    order: 2

services:
  - webapp.service

uploads:
  - source: configs/app.config
    destination: /opt/app/config.json
```

### Python API with Docker

```yaml
version: 1
template: docker
packages:
  - python3-pip

scripts:
  - name: deploy
    path: scripts/docker-deploy.sh
    order: 1

uploads:
  - source: files/docker-compose.yml
    destination: /opt/app/docker-compose.yml
  - source: files/.env
    destination: /opt/app/.env
    permissions: "600"
```

## Support

- GitHub Issues: https://github.com/sst/opencode/issues
- Documentation: This guide
- Examples: See `test-deployment/` directory
