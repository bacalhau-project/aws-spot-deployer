# Deployment Issues Found

## 1. Missing startup.py Script
- **Issue**: Cloud-init template references `startup.py` but it doesn't exist
- **Location**: Referenced in `instance/cloud-init/init-vm-template.yml` line 44 and 85
- **Impact**: Cloud-init fails when trying to run non-existent script
- **Solution**: Remove references since deployment is now handled by `deploy_services.py`

## 2. Reboot Command Missing sudo
- **Issue**: `deploy_services.py` tries to run `shutdown` without sudo
- **Fixed**: Changed to `sudo shutdown -r +1` (1 minute delay)

## 3. Service File References Wrong Path
- **Issue**: `bacalhau.service` expects docker-compose file at:
  `/opt/uploaded_files/scripts/docker-compose-bacalhau.yaml`
- **Reality**: File gets uploaded but service runs before files are moved to /opt

## 4. Deployment Flow Confusion
Current flow has multiple overlapping systems:
1. Old cloud-init tries to run startup.py 
2. New watcher waits for files and runs deploy_services.py
3. Services try to start before files are in place

## Root Cause
The deployment has been partially refactored from an old system (using startup.py and cloud-init) to a new system (using deploy_services.py and file upload), but remnants of the old system are still in the cloud-init template, causing conflicts.

## Quick Fix Needed
1. Remove startup.py references from cloud-init
2. Ensure services don't start until after deployment completes
3. Fix file paths in service files

## Recommended Approach
Use the simplified cloud-init (generate_minimal_cloud_init) that only:
- Sets up SSH
- Installs Docker and uv  
- Creates watcher script
- Waits for file upload

Then let deploy_services.py handle everything else after files are uploaded.