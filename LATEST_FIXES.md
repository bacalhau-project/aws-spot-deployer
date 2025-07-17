# Latest Deployment Fixes

## Docker Compose Installation Fix

### Problem
- `docker-compose-plugin` package doesn't exist in Ubuntu 22.04 repositories
- The service was failing because Docker Compose v2 wasn't available

### Solution
- Changed installation method to download directly from GitHub releases
- Updated both cloud-init and startup.py to use the same installation method:
  ```bash
  curl -sSL "https://github.com/docker/compose/releases/download/v2.32.1/docker-compose-linux-x86_64" \
    -o /usr/local/lib/docker/cli-plugins/docker-compose
  chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
  ```

## Quiet apt-get Commands

### Problem
- apt-get update/install commands were generating verbose output in logs

### Solution
- Modified `run_command()` function to automatically add `-qq` flag to apt-get commands
- This makes package operations quieter while still showing errors

## All Files Updated

1. **`deploy_spot.py`**:
   - Fixed docker-compose installation in cloud-init
   - Now downloads from GitHub releases instead of using apt

2. **`instance/scripts/startup.py`**:
   - Updated docker-compose installation method
   - Added quiet flags for apt commands
   - Fixed all linting issues

3. **`instance/scripts/bacalhau-startup.service`**:
   - Previously fixed circular dependency
   - Updated PATH for system-wide UV installation

## Quick Test Commands

```bash
# Destroy and recreate
uv run -s deploy_spot.py destroy
uv run -s deploy_spot.py create

# Check deployment (after ~5 minutes)
ssh -i ~/.ssh/your-key ubuntu@<ip> "sudo journalctl -u bacalhau-startup -n 50"
ssh -i ~/.ssh/your-key ubuntu@<ip> "docker compose version"
ssh -i ~/.ssh/your-key ubuntu@<ip> "docker ps -a"
```

## Expected Results

- Docker Compose v2.32.1 should be installed and working
- No verbose apt-get output in logs
- Services should start successfully
- Bacalhau containers should be running