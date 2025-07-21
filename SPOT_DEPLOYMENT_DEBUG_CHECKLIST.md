# Spot Deployment Debug Checklist

This is a targeted debugging checklist to identify issues in the spot deployment process. Test each item systematically to isolate the problem.

## Deployment Flow Overview

1. **Cloud-init** runs on boot (minimal setup)
2. **Watcher script** waits for file upload marker
3. **SSH file transfer** uploads files to `/tmp/uploaded_files/`
4. **Deploy script** (`deploy_services.py`) runs via SSH
5. **Services** are installed and scheduled to start after reboot

## 1. Cloud-Init Verification

### Test 1.1: Check cloud-init status
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<IP> "cloud-init status"
```
Expected: `status: done`

### Test 1.2: Verify cloud-init logs
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<IP> "sudo tail -50 /var/log/cloud-init-output.log"
```
Look for:
- Package installation success
- Docker installation
- uv installation
- Watcher script creation

### Test 1.3: Check if watcher is running
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<IP> "ps aux | grep watch-for-deployment"
```
Expected: Should see the watcher process

## 2. File Upload Verification

### Test 2.1: Check upload marker
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<IP> "ls -la /tmp/uploaded_files_ready"
```
Expected: File should exist after deployment

### Test 2.2: Verify uploaded files
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<IP> "find /tmp/uploaded_files -type f | head -20"
```
Expected: Should list uploaded files including:
- `/tmp/uploaded_files/scripts/deploy_services.py`
- `/tmp/uploaded_files/config/bacalhau-config.yaml`
- Service files (`.service`)

### Test 2.3: Check file count
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<IP> "find /tmp/uploaded_files -type f | wc -l"
```
Expected: Should match the count shown in deployment logs

## 3. Deployment Script Execution

### Test 3.1: Check deployment logs
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<IP> "cat /home/ubuntu/deployment.log"
```
Look for:
- Script start message
- Directory creation
- File movements
- Service installation

### Test 3.2: Check watcher log
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<IP> "cat /tmp/watcher.log"
```
Expected: Should show the watcher detected files and started deployment

### Test 3.3: Verify deployment completion marker
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<IP> "ls -la /opt/deployment_complete"
```
Expected: File should exist if deployment completed

## 4. Directory Structure

### Test 4.1: Check /opt directories
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<IP> "ls -la /opt/"
```
Expected directories:
- `/opt/uploaded_files/`
- `/opt/sensor/`
- `/opt/deployment.log`
- `/opt/startup.log`

### Test 4.2: Check Bacalhau directories
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<IP> "ls -la /bacalhau_node /bacalhau_data"
```
Expected: Both directories should exist with ubuntu:ubuntu ownership

### Test 4.3: Check sensor directories
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<IP> "ls -la /opt/sensor/"
```
Expected subdirectories: config, data, logs, exports

## 5. Service Installation

### Test 5.1: Check systemd services
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<IP> "ls -la /etc/systemd/system/*.service | grep -E '(bacalhau|sensor)'"
```
Expected:
- `bacalhau.service`
- `sensor-generator.service`

### Test 5.2: Check service status
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<IP> "systemctl status bacalhau.service sensor-generator.service"
```
Expected: Services should be enabled (but may not be running until after reboot)

### Test 5.3: Check for scheduled reboot
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<IP> "shutdown --show 2>/dev/null || echo 'No reboot scheduled'"
```
Expected: Should show a scheduled reboot if deployment completed

## 6. Software Dependencies

### Test 6.1: Check Docker
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<IP> "docker --version && systemctl is-active docker"
```
Expected: Docker version and "active"

### Test 6.2: Check uv installation
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<IP> "which uv && uv --version"
```
Expected: `/usr/local/bin/uv` or `/usr/bin/uv` and version output

### Test 6.3: Check user permissions
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<IP> "groups ubuntu"
```
Expected: ubuntu should be in docker group

## 7. Configuration Files

### Test 7.1: Check Bacalhau config
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<IP> "ls -la /bacalhau_node/config.yaml"
```
Expected: File should exist with proper permissions

### Test 7.2: Verify config has credentials
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<IP> "grep -E '(orchestrator|token)' /bacalhau_node/config.yaml | wc -l"
```
Expected: Should return count > 0 if credentials were injected

### Test 7.3: Check node identity
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<IP> "cat /opt/sensor/config/node_identity.json | jq '.sensor_id'"
```
Expected: Should show a sensor ID if identity was generated

## 8. Manual Deployment Test

If automated deployment failed, try running manually:

### Test 8.1: Run deployment script manually
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<IP>
cd /tmp/uploaded_files/scripts
sudo /usr/bin/uv run deploy_services.py
```
Watch for any errors in the output.

### Test 8.2: Run additional commands manually
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<IP>
sudo chmod +x /opt/uploaded_files/scripts/additional_commands.sh
sudo /opt/uploaded_files/scripts/additional_commands.sh
```

### Test 8.3: Generate node identity manually
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<IP>
cd /opt/uploaded_files/scripts
/usr/bin/uv run generate_node_identity.py
```

## 9. Post-Reboot Verification

After instance reboots:

### Test 9.1: Check Docker containers
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<IP> "docker ps"
```
Expected: Should see bacalhau container running

### Test 9.2: Check service logs
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<IP> "journalctl -u bacalhau.service -n 50"
```

### Test 9.3: Check Bacalhau node status
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@<IP> "docker exec bacalhau bacalhau node list"
```

## Common Issues and Solutions

1. **Watcher script not running**: Cloud-init may have failed. Check cloud-init logs.

2. **Files not in /opt**: The `deploy_services.py` script may have failed to move files from `/tmp`.

3. **Services not starting**: Check for dependency issues in service files.

4. **No reboot scheduled**: Deployment script didn't complete successfully.

5. **Permission errors**: Check file ownership and permissions throughout the process.

## Quick Debug Script

Save this as `debug_instance.sh`:

```bash
#!/bin/bash
IP=$1
if [ -z "$IP" ]; then
    echo "Usage: $0 <instance-ip>"
    exit 1
fi

SSH="ssh -i ~/.ssh/id_ed25519 ubuntu@$IP"

echo "=== Cloud-init Status ==="
$SSH "cloud-init status"

echo -e "\n=== Watcher Process ==="
$SSH "ps aux | grep watch-for-deployment | grep -v grep"

echo -e "\n=== Uploaded Files ==="
$SSH "find /tmp/uploaded_files -type f 2>/dev/null | wc -l"

echo -e "\n=== Deployment Logs ==="
$SSH "tail -20 /home/ubuntu/deployment.log 2>/dev/null || echo 'No deployment log found'"

echo -e "\n=== Systemd Services ==="
$SSH "systemctl list-unit-files | grep -E '(bacalhau|sensor)'"

echo -e "\n=== Docker Status ==="
$SSH "docker ps 2>/dev/null || echo 'Docker not running or not installed'"

echo -e "\n=== Directory Structure ==="
$SSH "ls -la /opt/ 2>/dev/null | grep -E '(uploaded_files|sensor|deployment)'"
$SSH "ls -la /bacalhau_node /bacalhau_data 2>/dev/null || echo 'Bacalhau dirs not found'"
```

Run with: `./debug_instance.sh <IP>`