# Deployment Fixes Summary

## Issues Identified and Fixed

### 1. **Service Script Mismatch**
- **Problem**: `bacalhau-startup.service` was looking for `simple-startup.py` but only `startup.py` was being referenced
- **Fix**: Already had `simple-startup.py` which is the correct minimal script without reboot
- **Status**: ✅ Fixed - Service correctly references `simple-startup.py`

### 2. **Missing Configuration File**
- **Problem**: `setup-config.service` expects `/opt/uploaded_files/config/bacalhau-config.yaml` but it didn't exist
- **Fix**: Created `instance/config/bacalhau-config.yaml` with basic Bacalhau configuration
- **Status**: ✅ Fixed

### 3. **File Movement Issue in Cloud-Init**
- **Problem**: Cloud-init was using `mv` which could fail if files were in use
- **Fix**: Changed to use `cp` (copy) instead of `mv` (move) for reliability
- **Status**: ✅ Fixed in `deploy_spot.py`

### 4. **Service Chain Conflicts**
- **Problem**: The old `startup.py` reboots the system, conflicting with systemd service management
- **Solution**: Using `simple-startup.py` which doesn't reboot and lets systemd handle services
- **Status**: ✅ Resolved

## Service Startup Order

The correct service startup sequence is:
1. `bacalhau-startup.service` - Initial setup, Docker verification
2. `setup-config.service` - Creates directories, copies configs, generates node identity
3. `bacalhau.service` & `sensor-generator.service` - Start Docker containers (in parallel)

## Files Created/Modified

1. **Created**: `instance/config/bacalhau-config.yaml` - Basic Bacalhau configuration
2. **Modified**: `deploy_spot.py` - Fixed file copying in cloud-init script
3. **Created**: `debug_deployment.sh` - Comprehensive debugging script
4. **Created**: `test_deployment_fixes.sh` - Quick verification script

## How to Test

1. **Before Deployment**: Run `./test_deployment_fixes.sh` to verify all files are in place
2. **Deploy**: `uv run -s deploy_spot.py create`
3. **After Deployment**: Run `./debug_deployment.sh <instance-ip>` to check deployment state

## Expected Behavior

After deployment:
- All files should be in `/opt/uploaded_files/scripts/` and `/opt/uploaded_files/config/`
- Services should start in the correct order
- No system reboot during service startup
- Docker containers should be running
- Node identity should be generated at `/opt/sensor/config/node_identity.json`

## Debugging Commands

If issues persist, SSH into the instance and run:
```bash
# Check service status
sudo systemctl status bacalhau-startup.service
sudo systemctl status setup-config.service

# Check logs
sudo journalctl -u bacalhau-startup.service -n 50
cat /opt/startup.log

# Check file locations
ls -la /opt/uploaded_files/scripts/
ls -la /opt/uploaded_files/config/

# Check Docker
docker ps -a
```