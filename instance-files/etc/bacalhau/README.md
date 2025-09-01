# Bacalhau Configuration

This directory contains Bacalhau orchestrator configuration files.

## Required Setup

### 1. Orchestrator Credentials

Copy the sample files and add your real orchestrator details:

```bash
cd instance-files/etc/bacalhau/
cp orchestrator_endpoint.sample orchestrator_endpoint
cp orchestrator_token.sample orchestrator_token
```

### 2. Update Configuration

Edit the files with your real orchestrator details:

**orchestrator_endpoint:**
```
nats://your-real-orchestrator.domain.com:4222
```

**orchestrator_token:**
```
your-real-orchestrator-token-from-expanso
```

## Deployment

During instance creation:
1. Credentials are read from these files
2. `bacalhau-config-template.yaml` variables are substituted
3. Final config is generated at `/bacalhau_node/config.yaml`
4. Bacalhau compute node connects to orchestrator

## Security

- ✅ Sample files (*.sample) are committed to git
- ❌ Real credential files are in .gitignore and NEVER committed
- ✅ Template variables are validated during deployment

## Files

- `orchestrator_endpoint.sample` - Example NATS endpoint
- `orchestrator_token.sample` - Example token
- `orchestrator_endpoint` - Your real endpoint (create this)
- `orchestrator_token` - Your real token (create this)
- `bacalhau-config-template.yaml` - Configuration template
- `README.md` - This documentation
