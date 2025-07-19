# Deployment Debug Checklist

Based on the current deployment flow, here's a systematic checklist to debug deployment issues:

## Current Deployment Flow

1. **Cloud-init runs** (`generate_minimal_cloud_init`):
   - Creates ubuntu user with SSH key
   - Installs packages: curl, wget, git, python3, docker
   - Installs uv to `/usr/bin/uv`
   - Creates watcher script at `/usr/local/bin/watch-for-deployment.sh`
   - Starts watcher in background that waits for `/tmp/uploaded_files_ready`

2. **Files are uploaded via SSH** (`transfer_files_scp`):
   - Creates `/tmp/uploaded_files/{scripts,config}` directories
   - Uploads scripts, configs, and user files to `/tmp/uploaded_files/`
   - Generates Bacalhau config with injected credentials
   - Creates `/tmp/uploaded_files_ready` marker file

3. **Watcher detects marker and runs deployment** (`deploy_services.py`):
   - Creates directories under `/opt/` with sudo
   - Moves files from `/tmp/uploaded_files/` to `/opt/uploaded_files/`
   - Copies service files to `/etc/systemd/system/`
   - Generates node identity
   - Enables systemd services
   - Schedules reboot in 3 seconds

4. **After reboot**:
   - Systemd services (bacalhau.service, sensor-generator.service) start
   - Docker containers run

## Manual Debug Steps

### Stage 1: Verify Cloud-Init Completed
```bash
ssh ubuntu@<IP> "sudo cloud-init status --wait"
ssh ubuntu@<IP> "cat /var/log/cloud-init-output.log | grep -E 'error|fail|warn'"
ssh ubuntu@<IP> "ls -la /usr/local/bin/watch-for-deployment.sh"
```

### Stage 2: Check Watcher Script
```bash
# Is watcher running?
ssh ubuntu@<IP> "ps aux | grep watch-for-deployment"

# Check watcher log
ssh ubuntu@<IP> "cat /tmp/watcher.log"

# Manually check what watcher is looking for
ssh ubuntu@<IP> "ls -la /tmp/uploaded_files_ready"
```

### Stage 3: Verify File Upload
```bash
# Check if files were uploaded
ssh ubuntu@<IP> "ls -la /tmp/uploaded_files/"

# Check if files were moved to /opt
ssh ubuntu@<IP> "ls -la /opt/uploaded_files/"

# Check specific critical files
ssh ubuntu@<IP> "ls -la /opt/uploaded_files/scripts/deploy_services.py"
ssh ubuntu@<IP> "ls -la /opt/uploaded_files/config/bacalhau-config.yaml"
```

### Stage 4: Check Deployment Execution
```bash
# Check deployment logs
ssh ubuntu@<IP> "cat ~/deployment.log"
ssh ubuntu@<IP> "cat /opt/deployment.log"

# Check if deployment completed
ssh ubuntu@<IP> "cat /opt/deployment_complete"
```

### Stage 5: Verify Services
```bash
# Check service files
ssh ubuntu@<IP> "ls -la /etc/systemd/system/ | grep -E 'bacalhau|sensor'"

# Check service status
ssh ubuntu@<IP> "systemctl status bacalhau.service"
ssh ubuntu@<IP> "journalctl -u bacalhau.service -n 50"

# Check Docker
ssh ubuntu@<IP> "docker ps -a"
```

### Stage 6: Common Failure Points

1. **Watcher not running**: Cloud-init might have failed to start it
2. **Files not found**: Upload might have failed or paths are wrong
3. **Permission errors**: `/opt` requires sudo, deployment script handles this
4. **UV not in PATH**: Check `/usr/bin/uv` exists
5. **Reboot didn't happen**: Check `uptime` to see if system rebooted

## Quick Diagnostic Script

Run the included `debug_deployment.sh` script:
```bash
./debug_deployment.sh <instance-ip> [ssh-key-path]
```

This will run all diagnostic commands and provide a summary.

## Manual Recovery Steps

If deployment failed at any stage:

1. **If watcher didn't run**:
   ```bash
   ssh ubuntu@<IP>
   # Check if files are there
   ls /tmp/uploaded_files/scripts/deploy_services.py
   # Run deployment manually
   cd /tmp/uploaded_files/scripts && /usr/bin/uv run deploy_services.py
   ```

2. **If files weren't moved**:
   ```bash
   ssh ubuntu@<IP>
   sudo mv /tmp/uploaded_files/* /opt/uploaded_files/
   sudo chown -R ubuntu:ubuntu /opt/uploaded_files
   ```

3. **If services weren't installed**:
   ```bash
   ssh ubuntu@<IP>
   sudo cp /opt/uploaded_files/scripts/*.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable bacalhau.service
   sudo systemctl start bacalhau.service
   ```

## Expected State After Successful Deployment

- `/opt/deployment_complete` exists
- `/opt/uploaded_files/` contains all scripts and configs
- `/bacalhau_node/config.yaml` exists with injected credentials
- `/opt/sensor/config/node_identity.json` exists
- `docker ps` shows running bacalhau container
- System has rebooted (check with `uptime`)