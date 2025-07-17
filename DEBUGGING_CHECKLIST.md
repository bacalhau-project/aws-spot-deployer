# Deployment Debugging Checklist

## 1. Cloud-Init Execution Verification
- [ ] **Check cloud-init logs**: SSH to instance and run `sudo cat /var/log/cloud-init-output.log`
- [ ] **Verify user data execution**: `cloud-init query userdata` to see what was executed
- [ ] **Check cloud-init status**: `cloud-init status --long` to ensure it completed
- [ ] **Verify uploaded files**: `ls -la /opt/uploaded_files/` and subdirectories

## 2. File Upload and Directory Structure
- [ ] **Verify base directories exist**:
  ```bash
  ls -la /opt/uploaded_files/
  ls -la /opt/uploaded_files/scripts/
  ls -la /opt/uploaded_files/config/
  ls -la /opt/uploaded_files/files/
  ```
- [ ] **Check file permissions**: All files should be readable by ubuntu user
- [ ] **Verify critical files**:
  ```bash
  ls -la /opt/uploaded_files/scripts/startup.py
  ls -la /opt/uploaded_files/scripts/simple-startup.py
  ls -la /opt/uploaded_files/scripts/generate_bacalhau_config.sh
  ls -la /opt/uploaded_files/orchestrator_endpoint
  ls -la /opt/uploaded_files/orchestrator_token
  ```

## 3. SystemD Service Chain
- [ ] **Check service status in order**:
  ```bash
  sudo systemctl status bacalhau-startup.service
  sudo systemctl status setup-config.service
  sudo systemctl status bacalhau.service
  sudo systemctl status sensor-generator.service
  ```
- [ ] **Check service logs**:
  ```bash
  sudo journalctl -u bacalhau-startup.service -n 100
  sudo journalctl -u setup-config.service -n 100
  sudo journalctl -u bacalhau.service -n 100
  ```
- [ ] **Verify service files copied**:
  ```bash
  ls -la /etc/systemd/system/bacalhau*.service
  ls -la /etc/systemd/system/setup-config.service
  ls -la /etc/systemd/system/sensor-generator.service
  ```

## 4. Startup Script Issues
- [ ] **Check startup.log**: `sudo cat /opt/startup.log`
- [ ] **Verify Python execution**:
  ```bash
  # Test if startup script can run
  sudo -u ubuntu python3 /opt/uploaded_files/scripts/startup.py
  # Check for Python errors
  python3 -m py_compile /opt/uploaded_files/scripts/startup.py
  ```
- [ ] **Check script naming**: File is referenced as both `startup.py` and `simple-startup.py`

## 5. Docker and Bacalhau Configuration
- [ ] **Verify Docker is running**: `sudo systemctl status docker`
- [ ] **Check Docker Compose installation**: `docker compose version`
- [ ] **Verify Bacalhau config generation**:
  ```bash
  sudo cat /bacalhau_node/config.yaml
  ls -la /bacalhau_node/
  ls -la /bacalhau_data/
  ```
- [ ] **Check Docker containers**: `docker ps -a`
- [ ] **Check compose logs**: `docker compose -f /opt/uploaded_files/scripts/docker-compose-bacalhau.yaml logs`

## 6. Directory Creation Issues
- [ ] **Verify all required directories**:
  ```bash
  ls -la /bacalhau_node/
  ls -la /bacalhau_data/
  ls -la /opt/sensor/config/
  ls -la /opt/sensor/data/
  ls -la /opt/sensor/logs/
  ls -la /opt/sensor/exports/
  ```
- [ ] **Check directory ownership**: All should be owned by ubuntu:ubuntu

## 7. Credential Files
- [ ] **Verify orchestrator credentials exist**:
  ```bash
  cat /opt/uploaded_files/orchestrator_endpoint
  cat /opt/uploaded_files/orchestrator_token
  ```
- [ ] **Check if config generation worked**:
  ```bash
  sudo /opt/uploaded_files/scripts/generate_bacalhau_config.sh
  cat /bacalhau_node/config.yaml | grep -A2 "Orchestrators\|Token"
  ```

## 8. Boot Sequence Timing
- [ ] **Check if services are starting too early**:
  ```bash
  systemctl list-dependencies multi-user.target | grep -E "(bacalhau|setup|sensor)"
  ```
- [ ] **Verify cloud-init completed before services**:
  ```bash
  systemctl show -p After bacalhau-startup.service
  ```

## 9. Common Root Causes

### Issue: startup.py vs simple-startup.py mismatch
- bacalhau-startup.service references `simple-startup.py`
- But the actual file might be `startup.py`
- **Fix**: Rename file or update service file

### Issue: Files not in expected location
- Cloud-init might be placing files in `/tmp/uploaded_files/` instead of `/opt/uploaded_files/`
- **Fix**: Update cloud-init to ensure correct destination

### Issue: Service dependency chain broken
- Services might be starting before cloud-init completes
- **Fix**: Ensure all services have `After=cloud-init.target`

### Issue: Permissions on executable scripts
- Scripts need execute permissions
- **Fix**: Add chmod +x in cloud-init for all scripts

## 10. Quick Debug Commands
```bash
# All-in-one status check
sudo systemctl status bacalhau*.service setup-config.service sensor*.service --no-pager

# Check all logs at once
sudo journalctl -u bacalhau*.service -u setup-config.service -u sensor*.service --since "10 minutes ago"

# Verify file structure
find /opt/uploaded_files -type f -ls

# Check Docker status
docker ps -a && docker compose -f /opt/uploaded_files/scripts/docker-compose-bacalhau.yaml logs --tail=50
```

## 11. Manual Recovery Steps
If services aren't starting automatically:
```bash
# 1. Create directories manually
sudo mkdir -p /bacalhau_node /bacalhau_data /opt/sensor/{config,data,logs,exports}
sudo chown -R ubuntu:ubuntu /bacalhau_node /bacalhau_data /opt/sensor

# 2. Generate config manually
sudo /opt/uploaded_files/scripts/generate_bacalhau_config.sh

# 3. Restart services
sudo systemctl daemon-reload
sudo systemctl restart bacalhau-startup.service
sudo systemctl restart setup-config.service
sudo systemctl restart bacalhau.service
```