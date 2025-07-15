# Deployment Fix Summary

## Issues Found and Fixed

### 1. **Race Condition: Cloud-init vs File Upload**
- **Problem**: Cloud-init was waiting for files that hadn't been uploaded yet
- **Solution**: Created a `configure-services.service` systemd unit that waits for files after boot
- **Result**: Services can now start after files are uploaded

### 2. **Service File Condition**
- **Problem**: `ConditionPathExists` in service files failed because files didn't exist at boot
- **Solution**: Removed condition and added dependency on `configure-services.service`
- **Result**: Services wait for proper configuration before starting

### 3. **Missing Directories**
- **Problem**: `/bacalhau_node`, `/bacalhau_data`, `/opt/sensor` were not created
- **Solution**: Added directory creation to cloud-init script
- **Result**: All required directories are created during initial setup

### 4. **Service Configuration Timing**
- **Problem**: Services were being enabled before files existed
- **Solution**: Moved service configuration to a separate systemd unit that runs after file upload
- **Result**: Services are only configured after all files are in place

### 5. **No Reboot Needed**
- **Problem**: System was rebooting unnecessarily, causing delays
- **Solution**: Removed reboot, services start immediately after configuration
- **Result**: Faster deployment, services start without reboot

## New Deployment Flow

1. **Cloud-init runs** → Creates directories, installs Docker, sets up base system
2. **SSH becomes available** → Main script connects and uploads files
3. **Files uploaded to `/tmp/exs`** → All scripts and service files uploaded
4. **configure-services.service triggered** → Waits for files, moves to correct locations
5. **Services configured and started** → No reboot needed, services start immediately

## Key Changes Made

### deploy_spot.py
- Removed cloud-init waiting for service files (was causing timeout)
- Created `configure-services.service` to handle post-upload configuration
- Updated `enable_startup_service()` to trigger configuration instead of reboot
- Removed unnecessary reboot from cloud-init

### bacalhau-startup.service
- Removed `ConditionPathExists` that was preventing startup
- Added dependency on `configure-services.service`
- Added file existence check in `ExecStartPre`
- Added restart on failure for resilience

## Testing the Fix

1. Deploy instances: `uv run -s deploy_spot.py create`
2. Wait for deployment to complete
3. Run debug: `./debug_runner.sh <instance-ip>`
4. Verify:
   - All directories exist
   - Files are in `/opt/uploaded_files/scripts/`
   - Services are running
   - Docker containers are active

## Benefits

- **No more race conditions** - Files are handled in proper order
- **Faster deployment** - No unnecessary reboots
- **More reliable** - Services only start when everything is ready
- **Better error handling** - Clear failure points if files are missing