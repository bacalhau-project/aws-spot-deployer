# Deployment Files Directory

This directory contains all files that will be deployed to AWS spot instances, including Bacalhau compute node configurations and any other application files.

## Files

- **bacalhau-config.yaml** - Configuration for connecting to the Bacalhau orchestrator
- **bacalhau-config.yaml.example** - Template configuration file (copy and modify)
- **docker-compose.yml** - Docker Compose configuration for running Bacalhau
- **setup-bacalhau.sh** - Setup script that installs and starts Bacalhau
- **bacalhau.service** - SystemD service file for managing Bacalhau

## Configuration

1. **Copy the example config**:
   ```bash
   cp bacalhau-config.yaml.example bacalhau-config.yaml
   ```

2. **Update the configuration** with your orchestrator details:
   - Set the orchestrator IP address
   - Update the NATS endpoint
   - Replace the authentication token

## How It Works

When you run `spot create`, the deployer will:

1. Create a tarball from this directory
2. Upload it to each instance
3. Extract it to `/opt/deployment/`
4. Run the setup script
5. Install the SystemD service
6. Start Bacalhau as a Docker container

Each node will automatically:
- Connect to the orchestrator
- Join the cluster
- Start processing jobs

## Customization

You can modify these files to:
- Change resource limits
- Add node labels
- Enable GPU support
- Adjust logging levels
- Configure different engines

## Security Note

The `bacalhau-config.yaml` file contains your authentication token and is listed in `.gitignore` to prevent accidental commits. Always use the example file as a template.