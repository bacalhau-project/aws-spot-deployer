# Bacalhau Orchestrator Configuration

To connect Bacalhau compute nodes to an orchestrator, you need to provide the orchestrator endpoint and authentication token.

## Setup

1. Copy the example files:
   ```bash
   cp orchestrator_endpoint.example orchestrator_endpoint
   cp orchestrator_token.example orchestrator_token
   ```

2. Edit `orchestrator_endpoint` and add your NATS endpoint:
   ```
   nats://your-orchestrator-host:4222
   ```

3. Edit `orchestrator_token` and add your authentication token:
   ```
   your-secret-token-here
   ```

## How It Works

1. During deployment, these files are uploaded to `/opt/bacalhau/` on each node
2. The `bacalhau.service` reads these files during startup
3. The service generates a complete `/bacalhau_node/config.yaml` with orchestrator settings

## Security Notes

- Never commit the actual `orchestrator_endpoint` or `orchestrator_token` files to git (they're in .gitignore)
- Keep your orchestrator tokens secure and rotate them regularly
- Use network security groups to restrict access to the orchestrator

## Optional Configuration

If these files are missing, compute nodes will start but won't connect to any orchestrator. They will run in standalone mode.
