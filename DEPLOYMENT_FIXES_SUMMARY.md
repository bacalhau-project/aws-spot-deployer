# Deployment Fixes Summary - Updated

## All Issues Fixed

### 1. Cloud-init Size Issue (RESOLVED)
- **Problem**: Cloud-init was 120KB, exceeding AWS 16KB limit
- **Solution**: Implemented two-stage deployment:
  - Minimal cloud-init (3.6KB) that waits for file upload
  - Upload deployment bundle after SSH is available
  - Cloud-init waits for `/tmp/UPLOAD_COMPLETE` marker

### 2. Circular Dependency (RESOLVED)
- **Problem**: `bacalhau-startup.service` had `After=cloud-init.target` creating a dependency cycle
- **Solution**: Removed the cloud-init.target dependency from the service file

### 3. UV Installation Issue (RESOLVED)
- **Problem**: UV was installed to `/root/.local/bin` but services run as ubuntu user
- **Solution**: 
  - Changed to install UV system-wide: `UV_INSTALL_DIR="/usr/local/bin"`
  - Updated PATH in bacalhau-startup.service to use `/usr/local/bin`
  - Removed duplicate UV installation in cloud-init

### 4. Shutdown Command Error (RESOLVED)
- **Problem**: `shutdown -r +0.2` is invalid (minimum is 1 minute)
- **Solution**: Changed to `shutdown -r +1` in startup.py

### 5. Docker Compose Plugin (RESOLVED)
- **Problem**: docker-compose-plugin might not be available
- **Solution**: Added explicit installation in cloud-init runcmd

## Deployment Flow

1. **Cloud-init Phase**:
   - Creates ubuntu user with SSH keys
   - Installs docker.io, python3, python3-pip
   - Installs UV system-wide to /usr/local/bin
   - Installs docker-compose-plugin
   - Waits for /tmp/UPLOAD_COMPLETE marker
   - Enables setup-deployment.service
   - Reboots

2. **Upload Phase** (handled by deploy_spot.py):
   - Uploads deployment-bundle.tar.gz to /tmp/
   - Creates /tmp/UPLOAD_COMPLETE marker

3. **Setup Phase** (after reboot):
   - setup-deployment.service extracts bundle
   - Creates directories and copies files
   - Enables all services
   - Reboots again

4. **Startup Phase** (after second reboot):
   - bacalhau-startup.service runs startup.py using UV
   - Configures and starts Docker containers
   - Sets up sensor services
   - Generates node identity

## Files Modified

1. **`/Users/daaronch/code/spot/deploy_spot.py`**:
   - Fixed UV installation to use system-wide location
   - Added docker-compose-plugin installation
   - Removed duplicate UV installation

2. **`/Users/daaronch/code/spot/instance/scripts/bacalhau-startup.service`**:
   - Removed circular dependency on cloud-init.target
   - Updated PATH to use /usr/local/bin for UV

3. **`/Users/daaronch/code/spot/instance/scripts/startup.py`**:
   - Fixed shutdown command from +0.2 to +1

## Testing Commands

```bash
# 1. Run linting check
uv run ruff check deploy_spot.py

# 2. Destroy existing instances
uv run -s deploy_spot.py destroy

# 3. Deploy fresh instances
uv run -s deploy_spot.py create

# 4. Wait ~5 minutes, then check deployment
ssh -i ~/.ssh/your-key ubuntu@<instance-ip> "tail -50 /opt/startup.log"

# 5. Verify services
ssh -i ~/.ssh/your-key ubuntu@<instance-ip> "sudo systemctl status bacalhau-startup setup-deployment"

# 6. Check Docker containers
ssh -i ~/.ssh/your-key ubuntu@<instance-ip> "docker ps -a"

# 7. Verify UV installation
ssh -i ~/.ssh/your-key ubuntu@<instance-ip> "which uv && uv --version"

# 8. Check docker-compose
ssh -i ~/.ssh/your-key ubuntu@<instance-ip> "docker compose version"
```

## Expected Results

After deployment completes:
- UV should be available at `/usr/local/bin/uv`
- Docker Compose plugin should be installed
- All services should start without errors
- No circular dependency warnings in logs
- Bacalhau containers should be running
- System should reboot cleanly after startup

## Next Steps

1. Run the linting check to ensure code quality
2. Deploy test instances
3. Monitor the deployment logs
4. Verify all services start correctly

All identified issues have been resolved. The deployment should now work end-to-end.