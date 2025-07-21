# Fix Deployment Action Plan

## Immediate Actions Required

### 1. Test Current Deployment
First, let's verify what's happening on existing instances:

```bash
# Pick an instance IP from instances.json
IP=18.159.108.71  # or any instance IP

# Run the debug script
./debug_instance.sh $IP
```

### 2. Key Issues to Fix

#### Issue 1: Premature Reboot
The system is rebooting too quickly (1 minute) which might not give enough time for deployment to complete.

**Fix**: Increase reboot delay or make it conditional
- Edit `instance/scripts/deploy_services.py` line 211
- Change from 1 minute to 5 minutes or remove automatic reboot

#### Issue 2: Service Path Mismatch  
Services expect files in `/opt/uploaded_files/scripts/` but docker-compose files need proper setup.

**Fix**: Update service files to use correct paths after deployment

#### Issue 3: Missing Bacalhau Config
The bacalhau.service expects config at `/bacalhau_node/config.yaml` but it needs to be copied there.

**Already handled** by deploy_services.py in `copy_configuration_files()`

### 3. Debug Steps for Stuck Instance

If instance is stuck in shutdown state:
1. Wait 5-10 minutes for it to come back
2. If it doesn't, the instance needs to be destroyed and recreated
3. AWS spot instances sometimes fail to reboot properly

### 4. Quick Test Commands

```bash
# Check if instance is truly down or just refusing SSH
aws ec2 describe-instances --instance-ids i-040aa49cdb1213b93 --query 'Reservations[0].Instances[0].State'

# Force stop and start if needed
aws ec2 stop-instances --instance-ids i-040aa49cdb1213b93
# Wait a bit
aws ec2 start-instances --instance-ids i-040aa49cdb1213b93
```

### 5. Recommended Next Steps

1. **Destroy current deployment** (since instances are in bad state):
   ```bash
   ./spot-dev destroy
   ```

2. **Remove automatic reboot** from deploy_services.py or increase delay significantly

3. **Deploy fresh instances**:
   ```bash
   ./spot-dev create
   ```

4. **Monitor deployment** using the debug script on a new instance

5. **Manually verify** deployment completed before any reboot

### 6. Long-term Fix

Consider removing automatic reboot entirely and instead:
- Let deployment complete
- Start services without reboot using systemctl
- Only reboot if explicitly needed

This would prevent the "stuck in shutdown" issue entirely.