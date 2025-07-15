# Deployment Fix Plan

## Problem Summary

The current deployment is failing because:
1. Files are uploaded to `/tmp/exs` and `/tmp/uploaded_files` but not moved to final locations
2. SystemD services are not being installed (remain in temp directories)
3. The cloud-init configure-services script is not executing properly
4. Complex race conditions between cloud-init and our deployment process

## Root Cause Analysis

The deployment has too many moving parts with unclear ownership:
- Cloud-init creates configure-services that waits for files
- File upload happens after cloud-init
- Configure-services is supposed to move files and enable services
- But the timing and execution is unreliable

## Proposed Solution

### 1. Clear Separation of Responsibilities

**Cloud-init responsibilities (minimal)**:
- Install packages (Docker, Python, etc.)
- Create ubuntu user with SSH keys
- Create base directories
- Mark completion with `/tmp/cloud-init-complete`

**Our deployment script responsibilities (everything else)**:
- Wait for cloud-init completion
- Create all application directories
- Move files from upload locations to final destinations
- Install SystemD services
- Enable and start services
- Handle configuration files
- Schedule clean reboot

### 2. Implementation Steps

1. **Simplify cloud-init** - Remove all configure-services logic
2. **Create deployment script** - `deploy_services.py` handles all post-upload logic
3. **Update deploy_spot.py** - Execute deployment script instead of configure-services
4. **Test thoroughly** - Ensure clean deployment with no race conditions

### 3. File Flow

```
Upload Phase:
  deploy_spot.py -> SCP files to -> /tmp/exs/ and /tmp/uploaded_files/

Deployment Phase:
  deploy_spot.py -> SSH execute -> /tmp/deploy_services.py
    |
    v
  deploy_services.py:
    - Wait for cloud-init
    - Move /tmp/exs/*.service -> /etc/systemd/system/
    - Move /tmp/exs/* -> /opt/uploaded_files/scripts/
    - Move /tmp/uploaded_files/config/* -> /opt/uploaded_files/config/
    - Copy configs to final locations
    - Enable all services
    - Run startup.py
    - Schedule reboot
```

### 4. Key Changes

1. **deploy_spot.py changes**:
   - Remove configure-services from cloud-init
   - Update `enable_startup_service()` to upload and execute `deploy_services.py`

2. **New deploy_services.py**:
   - Single Python script that handles all deployment logic
   - Clear logging to `/opt/deployment.log`
   - Proper error handling and recovery

3. **Testing approach**:
   - Use `test_deployment_fix.sh` to validate deployment
   - Check service status, file locations, and logs

## Benefits

1. **Simplicity**: One script owns all deployment logic
2. **Reliability**: No race conditions or timing issues
3. **Debuggability**: Clear logs and single execution path
4. **Maintainability**: Easy to modify deployment without touching cloud-init

## Next Steps

1. Deploy test instance with new code
2. Run `test_deployment_fix.sh` to validate
3. Monitor for successful service startup
4. Document any remaining issues

## Success Criteria

- All files in correct locations
- All services enabled and running
- Clean deployment log showing each step
- Successful reboot with services starting automatically