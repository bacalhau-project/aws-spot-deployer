# Test Execution Guide

This guide explains how to use the debug tools to systematically test and fix deployment issues.

## Quick Start

### 1. Run Automated Debug
```bash
# Basic debug (just checks)
./debug_runner.sh <instance-ip>

# Debug with auto-fix attempts
./debug_runner.sh <instance-ip> --fix
```

### 2. Run Individual Tests
```bash
# Test cloud-init completion
./debug_test_cloud_init.sh <instance-ip>

# Test directory structure and files
./debug_test_directories.sh <instance-ip>

# Test systemd services
./debug_test_services.sh <instance-ip>

# Test Docker containers
./debug_test_containers.sh <instance-ip>
```

## Test Descriptions

### debug_runner.sh
- **Purpose**: Runs all tests automatically and generates a report
- **Output**: Creates `debug_report_YYYYMMDD_HHMMSS/` directory with full results
- **Fix Mode**: Can attempt automatic fixes for common issues

### debug_test_cloud_init.sh
- **Tests**: Cloud-init completion, package installation, error detection
- **Key Checks**:
  - Cloud-init status (should be "done")
  - Package installation (Docker, Python, etc.)
  - Error count in logs
  - System uptime to verify reboot

### debug_test_directories.sh
- **Tests**: Directory creation, file upload, permissions
- **Key Checks**:
  - All required directories exist
  - Scripts and configs uploaded
  - Service files installed in systemd
  - Correct permissions and ownership

### debug_test_services.sh
- **Tests**: SystemD service status, logs, dependencies
- **Key Checks**:
  - Service installation and enablement
  - Service status (active/failed/inactive)
  - Service dependencies and order
  - Service logs for errors

### debug_test_containers.sh
- **Tests**: Docker installation, container status, logs
- **Key Checks**:
  - Docker daemon running
  - Containers created and running
  - Node identity generated
  - Port availability

## Common Issues and Solutions

### Issue 1: "Scripts missing"
**Solution**: Re-run deployment
```bash
uv run -s deploy_spot.py destroy
uv run -s deploy_spot.py create
```

### Issue 2: "Docker not working"
**Solution**: Fix Docker installation
```bash
./fix_docker.sh
# or
./debug_runner.sh <instance-ip> --fix
```

### Issue 3: "Services failed"
**Solution**: Check logs and restart
```bash
# SSH to instance
ssh -i ~/.ssh/your-key.pem ubuntu@<instance-ip>

# Check specific service
sudo journalctl -u bacalhau-startup.service -n 50

# Restart service
sudo systemctl restart bacalhau-startup.service
```

### Issue 4: "No containers running"
**Solution**: Start containers manually
```bash
# SSH to instance
ssh -i ~/.ssh/your-key.pem ubuntu@<instance-ip>

# Start containers
cd /opt/uploaded_files/scripts
docker compose -f docker-compose-bacalhau.yaml up -d
docker compose -f docker-compose-sensor.yaml up -d
```

## Debug Workflow

1. **Deploy instances**
   ```bash
   uv run -s deploy_spot.py create
   ```

2. **Wait 3-5 minutes** for cloud-init to complete

3. **Run automated debug**
   ```bash
   ./debug_runner.sh <instance-ip>
   ```

4. **Review report**
   ```bash
   cat debug_report_*/debug_report.txt
   ```

5. **Fix issues based on recommendations**

6. **Re-run specific tests to verify fixes**

## Understanding Test Output

### Success Indicators
- ✅ Green checkmarks indicate success
- "active" status for services
- Docker containers running
- Node identity file exists

### Warning Indicators
- ⚠️ Yellow warnings indicate optional items or minor issues
- "inactive" services that haven't started yet
- Optional files missing

### Failure Indicators
- ❌ Red X marks indicate failures
- "failed" service status
- Missing required directories
- Docker daemon not running

## Manual Debug Commands

If automated tests aren't sufficient, use these commands on the instance:

```bash
# Full cloud-init log
sudo cat /var/log/cloud-init-output.log

# Service status details
systemctl status <service-name> -l

# Docker troubleshooting
docker ps -a
docker logs <container-name>

# File permissions
ls -la /opt/uploaded_files/scripts/

# Process check
ps aux | grep -E "(python|docker)"

# Network check
netstat -tuln | grep -E "(1234|8080)"
```

## Tips

1. **Always wait for cloud-init** to complete before debugging
2. **Run debug_runner.sh first** for a comprehensive overview
3. **Use --fix mode** for automatic fixes of common issues
4. **Check timestamps** in logs to understand execution order
5. **Save debug reports** for comparison between runs