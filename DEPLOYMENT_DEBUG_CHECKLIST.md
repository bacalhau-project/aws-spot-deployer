# AWS Spot Instance Deployment Debug Checklist

This checklist helps systematically debug deployment issues when instances are created but services aren't running properly.

## Quick Start

```bash
# Run automated debug script
./debug_deployment.sh <instance-ip> <ssh-key-path>

# Example
./debug_deployment.sh 52.34.56.78 ~/.ssh/my-key.pem
```

## Manual Debug Checklist

### 1. SSH Connectivity Test
```bash
ssh -i <key> ubuntu@<ip> "echo 'Connected'"
```
- ✅ **Pass**: Continue to next step
- ❌ **Fail**: Check security groups, SSH key, instance state

### 2. Cloud-Init Status
```bash
ssh -i <key> ubuntu@<ip> "sudo cloud-init status"
```
- ✅ **Expected**: `status: done`
- ❌ **If running/error**: Check cloud-init logs:
  ```bash
  ssh -i <key> ubuntu@<ip> "sudo tail -100 /var/log/cloud-init-output.log"
  ```

### 3. Watcher Script Check
```bash
# Check if watcher script exists
ssh -i <key> ubuntu@<ip> "ls -la /usr/local/bin/watch-for-deployment.sh"

# Check if watcher is running
ssh -i <key> ubuntu@<ip> "ps aux | grep watch-for-deployment"

# Check watcher log
ssh -i <key> ubuntu@<ip> "cat /tmp/watcher.log"
```

**Common Issues**:
- ❌ **Script missing**: Cloud-init failed
- ❌ **Not running**: Start manually:
  ```bash
  ssh -i <key> ubuntu@<ip> "nohup /usr/local/bin/watch-for-deployment.sh > /tmp/watcher.log 2>&1 &"
  ```

### 4. File Upload Verification
```bash
# Check upload directory
ssh -i <key> ubuntu@<ip> "ls -la /tmp/uploaded_files/"

# Check marker file
ssh -i <key> ubuntu@<ip> "ls -la /tmp/uploaded_files/marker"

# List all uploaded files
ssh -i <key> ubuntu@<ip> "find /tmp/uploaded_files -type f"
```

**Common Issues**:
- ❌ **No files**: Upload failed, check deploy_spot.py logs
- ❌ **No marker**: Create manually:
  ```bash
  ssh -i <key> ubuntu@<ip> "touch /tmp/uploaded_files/marker"
  ```

### 5. Deploy Services Script
```bash
# Check deployment log
ssh -i <key> ubuntu@<ip> "cat ~/deployment.log"

# Check if deploy_services.py exists
ssh -i <key> ubuntu@<ip> "ls -la /tmp/uploaded_files/scripts/deploy_services.py"
```

**If not run**, trigger manually:
```bash
ssh -i <key> ubuntu@<ip> "cd /tmp/uploaded_files/scripts && sudo /usr/bin/uv run deploy_services.py"
```

### 6. Docker and UV Installation
```bash
# Check Docker
ssh -i <key> ubuntu@<ip> "docker --version"

# Check UV
ssh -i <key> ubuntu@<ip> "uv --version"
ssh -i <key> ubuntu@<ip> "which uv"
```

**Common Issues**:
- ❌ **UV not in PATH**: Add to PATH:
  ```bash
  ssh -i <key> ubuntu@<ip> "echo 'export PATH=/usr/bin:$PATH' >> ~/.bashrc"
  ```

### 7. Directory Structure
```bash
# Check all required directories
ssh -i <key> ubuntu@<ip> "ls -la /opt/"
ssh -i <key> ubuntu@<ip> "ls -la /opt/scripts/"
ssh -i <key> ubuntu@<ip> "ls -la /opt/uploaded_files/"
ssh -i <key> ubuntu@<ip> "ls -la /opt/sensor/config/"
```

**If missing**, create manually:
```bash
ssh -i <key> ubuntu@<ip> "sudo mkdir -p /opt/{scripts,uploaded_files,sensor/config}"
```

### 8. SystemD Services
```bash
# Check service status
ssh -i <key> ubuntu@<ip> "systemctl status bacalhau-startup"
ssh -i <key> ubuntu@<ip> "systemctl status bacalhau"
ssh -i <key> ubuntu@<ip> "systemctl status sensor"

# Check if services are enabled
ssh -i <key> ubuntu@<ip> "systemctl is-enabled bacalhau-startup"
```

**If not installed**:
```bash
# Copy service files
ssh -i <key> ubuntu@<ip> "sudo cp /tmp/uploaded_files/scripts/*.service /etc/systemd/system/"
ssh -i <key> ubuntu@<ip> "sudo systemctl daemon-reload"
ssh -i <key> ubuntu@<ip> "sudo systemctl enable bacalhau-startup bacalhau sensor"
```

### 9. Startup Script Output
```bash
# Check startup log
ssh -i <key> ubuntu@<ip> "cat /opt/startup.log"

# Run startup manually if needed
ssh -i <key> ubuntu@<ip> "cd /opt/scripts && sudo /usr/bin/uv run startup.py"
```

### 10. Node Identity
```bash
# Check if generated
ssh -i <key> ubuntu@<ip> "cat /opt/sensor/config/node_identity.json | jq ."
```

**If missing**, generate manually:
```bash
ssh -i <key> ubuntu@<ip> "cd /opt/scripts && INSTANCE_ID=$(ec2-metadata --instance-id | cut -d' ' -f2) sudo /usr/bin/uv run generate_node_identity.py"
```

## Common Root Causes

### 1. Timing Issue
**Symptom**: Marker file created before all files uploaded
**Fix**: 
```bash
# Remove marker and recreate after verifying files
ssh -i <key> ubuntu@<ip> "rm /tmp/uploaded_files/marker"
# Verify all files are present
ssh -i <key> ubuntu@<ip> "ls -la /tmp/uploaded_files/scripts/"
# Recreate marker
ssh -i <key> ubuntu@<ip> "touch /tmp/uploaded_files/marker"
```

### 2. Permission Issues
**Symptom**: Can't move files from /tmp to /opt
**Fix**:
```bash
ssh -i <key> ubuntu@<ip> "sudo chown -R root:root /tmp/uploaded_files"
ssh -i <key> ubuntu@<ip> "cd /tmp/uploaded_files/scripts && sudo /usr/bin/uv run deploy_services.py"
```

### 3. UV Path Issues
**Symptom**: UV not found when running scripts
**Fix**:
```bash
# Use full path
ssh -i <key> ubuntu@<ip> "sudo /usr/bin/uv --version"
# Or update PATH in scripts
ssh -i <key> ubuntu@<ip> "sudo sed -i '1a export PATH=/usr/bin:$PATH' /opt/scripts/*.py"
```

### 4. Reboot Not Triggered
**Symptom**: Services installed but not started
**Fix**:
```bash
# Manually reboot
ssh -i <key> ubuntu@<ip> "sudo reboot"
# Wait 30 seconds, then check services
ssh -i <key> ubuntu@<ip> "systemctl status bacalhau"
```

## Full Recovery Procedure

If deployment is completely broken, run this sequence:

```bash
# 1. Set variables
IP="<instance-ip>"
KEY="<ssh-key-path>"

# 2. Ensure watcher is running
ssh -i $KEY ubuntu@$IP "nohup /usr/local/bin/watch-for-deployment.sh > /tmp/watcher.log 2>&1 &"

# 3. Verify files are uploaded
ssh -i $KEY ubuntu@$IP "ls -la /tmp/uploaded_files/scripts/"

# 4. Create marker if missing
ssh -i $KEY ubuntu@$IP "touch /tmp/uploaded_files/marker"

# 5. Wait for watcher to trigger (or run manually)
sleep 10
ssh -i $KEY ubuntu@$IP "cat ~/deployment.log"

# 6. If deployment didn't run, trigger manually
ssh -i $KEY ubuntu@$IP "cd /tmp/uploaded_files/scripts && sudo /usr/bin/uv run deploy_services.py"

# 7. Check if reboot is needed
ssh -i $KEY ubuntu@$IP "systemctl is-active bacalhau || sudo reboot"
```

## Log Locations

- **Cloud-init**: `/var/log/cloud-init-output.log`
- **Watcher script**: `/tmp/watcher.log`
- **Deployment**: `~/deployment.log`
- **Startup script**: `/opt/startup.log`
- **SystemD services**: `journalctl -u <service-name>`
- **Docker compose**: `/opt/uploaded_files/docker-compose.log`

## Quick Commands Reference

```bash
# View all error messages
ssh -i <key> ubuntu@<ip> "grep -i error /tmp/watcher.log ~/deployment.log /opt/startup.log 2>/dev/null"

# Check everything at once
./debug_deployment.sh <ip> <key>

# Force full deployment
ssh -i <key> ubuntu@<ip> "cd /tmp/uploaded_files/scripts && sudo /usr/bin/uv run deploy_services.py && sudo reboot"

# Monitor deployment in real-time
ssh -i <key> ubuntu@<ip> "tail -f /tmp/watcher.log ~/deployment.log"
```