# Deployment Fix Testing Guide

## Quick Test Procedure

### 1. Deploy a Test Instance
```bash
uv run -s deploy_spot.py create
```

Wait for the instance to show as "Created" in the deployment output.

### 2. Run the Fix Test
```bash
# Get the instance IP from the deployment output or:
uv run -s deploy_spot.py list

# Test the deployment fix
./test_deployment_fix.sh <instance-ip>
```

### 3. Expected Output

You should see:
- Deployment script uploads successfully
- All services show as "enabled"
- Files appear in `/opt/uploaded_files/scripts`
- Configuration files are copied to their destinations
- Deployment log shows successful completion

### 4. Verify Services Are Running

After the system reboots (1 minute after deployment):
```bash
ssh ubuntu@<instance-ip> "sudo systemctl status bacalhau.service sensor-generator.service"
```

## If Issues Persist

1. Check the deployment log:
```bash
ssh ubuntu@<instance-ip> "cat /opt/deployment.log"
```

2. Check cloud-init status:
```bash
ssh ubuntu@<instance-ip> "cloud-init status --long"
```

3. Run the full debug script:
```bash
./debug_deployment.sh <instance-ip>
```

## What Changed

1. **Removed complex cloud-init logic** - No more configure-services waiting for files
2. **Single deployment script** - `deploy_services.py` handles everything
3. **Clear execution order** - Upload files → Execute deployment script → Reboot
4. **Better logging** - All actions logged to `/opt/deployment.log`

## Success Indicators

- ✅ All services enabled in systemd
- ✅ Files in `/opt/uploaded_files/scripts`
- ✅ Configs in correct locations
- ✅ Clean reboot with services starting
- ✅ No "waiting for files" messages