# Deployment Files Directory

This directory contains all files that will be deployed to AWS spot instances. The directory structure mirrors the actual filesystem layout on the target servers.

## Directory Structure

```
deployment-files/
├── etc/
│   ├── bacalhau/           # Bacalhau configuration files
│   │   ├── config.yaml     # Main Bacalhau config (gitignored)
│   │   ├── orchestrator_endpoint  # NATS endpoint (gitignored)
│   │   └── orchestrator_token     # Auth token (gitignored)
│   └── systemd/
│       └── system/         # SystemD service files
│           └── bacalhau.service
├── opt/
│   └── bacalhau/          # Bacalhau runtime files
│       └── docker-compose.yml
└── setup.sh               # Main setup script
```

## How It Works

1. **Tarball Creation**: The entire `deployment-files/` directory is tarred and uploaded to instances
2. **Extraction**: Files are extracted to `/opt/deployment/` maintaining the directory structure
3. **Setup Script**: The `setup.sh` script copies files to their final locations:
   - `/opt/deployment/etc/bacalhau/config.yaml` → `/etc/bacalhau/config.yaml`
   - `/opt/deployment/opt/bacalhau/docker-compose.yml` → `/opt/bacalhau/docker-compose.yml`
   - `/opt/deployment/etc/systemd/system/bacalhau.service` → `/etc/systemd/system/bacalhau.service`
4. **Service Start**: The setup script starts the Bacalhau service

## Configuration

Before deployment, create the required configuration files:

```bash
# Copy from examples (if they exist)
cp etc/bacalhau/orchestrator_endpoint.example etc/bacalhau/orchestrator_endpoint
cp etc/bacalhau/orchestrator_token.example etc/bacalhau/orchestrator_token

# Edit with your values
echo "nats://your-orchestrator:4222" > etc/bacalhau/orchestrator_endpoint
echo "your-auth-token" > etc/bacalhau/orchestrator_token
```

## Adding New Files

To add new files to the deployment:

1. Place them in the appropriate directory matching their final location
2. Update `setup.sh` to copy them to their final location
3. The tarball will automatically include them

Example: To add a config file that should be at `/etc/myapp/config.yaml`:
1. Create `deployment-files/etc/myapp/config.yaml`
2. Add to `setup.sh`: `cp /opt/deployment/etc/myapp/config.yaml /etc/myapp/config.yaml`

## Security Note

The following files contain sensitive information and are gitignored:
- `etc/bacalhau/config.yaml`
- `etc/bacalhau/orchestrator_endpoint`
- `etc/bacalhau/orchestrator_token`

Always use the `.example` files as templates and never commit actual credentials.