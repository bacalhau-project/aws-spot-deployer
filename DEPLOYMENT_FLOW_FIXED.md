# Deployment Flow Fixed

## Changes Made

### 1. Removed Reboot from deploy_services.py
- The deployment script no longer schedules its own reboot
- It simply marks deployment as complete
- Cloud-init handles the reboot after all steps complete

### 2. Updated Cloud-Init Flow
The new flow is sequential and deterministic:

1. **Cloud-init starts**
   - Creates users and SSH keys
   - Installs packages (Docker, uv, etc.)
   
2. **Waits for file upload**
   - Waits up to 5 minutes for `/tmp/uploaded_files_ready` marker
   - This marker is created by SSH file transfer after cloud-init
   
3. **Runs deploy_services.py**
   - Moves files from /tmp to /opt
   - Installs systemd services
   - Configures Bacalhau and sensor
   
4. **Runs additional_commands.sh**
   - Handles sensor-specific setup
   - Generates node identity
   
5. **Cloud-init reboots the system**
   - Uses proper power_state directive
   - Clean reboot after all deployment completes

## Benefits

1. **No more stuck shutdowns** - Cloud-init handles reboot properly
2. **Sequential execution** - Each step completes before the next
3. **Proper error handling** - Timeouts and error messages at each stage
4. **Clean logs** - Everything logged to /opt/startup.log and /opt/deployment.log

## Testing the Fix

1. Destroy existing instances (they're in bad state):
   ```bash
   ./spot-dev destroy
   ```

2. Deploy new instances:
   ```bash
   ./spot-dev create
   ```

3. Monitor deployment on a test instance:
   ```bash
   # Pick an instance IP and watch the logs
   ssh -i ~/.ssh/id_ed25519 ubuntu@<IP> "tail -f /opt/startup.log"
   ```

4. After reboot, verify services:
   ```bash
   ./debug_instance.sh <IP>
   ```

## Expected Timeline

1. **0-2 minutes**: Cloud-init runs, installs packages
2. **2-3 minutes**: SSH available, file upload starts
3. **3-4 minutes**: Files uploaded, deployment script runs
4. **4-5 minutes**: Services installed, additional commands run
5. **5-6 minutes**: System reboots
6. **7-8 minutes**: System back up with all services running

## Key Files

- `/opt/startup.log` - Main deployment log
- `/opt/deployment.log` - Detailed deployment script output
- `/home/ubuntu/deployment.log` - User-accessible copy
- `/opt/deployment_complete` - Marker file when deployment succeeds