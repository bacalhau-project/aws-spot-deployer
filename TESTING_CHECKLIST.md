# Testing Checklist

Use this checklist to manually verify all functionality works correctly with AWS.

## Pre-Test Setup ✅

- [ ] AWS credentials configured (`aws sts get-caller-identity`)
- [ ] SSH keys exist (`ls ~/.ssh/id_ed25519*`)
- [ ] Test config created with minimal resources
- [ ] AWS billing alerts configured
- [ ] Using test/sandbox AWS account (if available)

## Basic Functionality Tests ✅

### 1. List Command (Safe)
- [ ] Run: `python -m spot_deployer.main list`
- [ ] Verify: Shows "No instances found" initially
- [ ] Verify: Progress messages appear

### 2. Create Command
- [ ] Run: `python -m spot_deployer.main create --config test-config.yaml`
- [ ] Verify: Shows "Reading configuration..."
- [ ] Verify: Shows deployment plan (regions and instance counts)
- [ ] Verify: Shows "Preparing deployment resources..."
- [ ] Verify: Live table updates with instance progress
- [ ] Verify: Shows "Waiting for public IP" status
- [ ] Verify: Shows "Uploading files" progress
- [ ] Verify: Shows "SUCCESS: Created" for each instance
- [ ] Verify: Final summary table appears
- [ ] Check: `instances.json` contains instance data

### 3. List Command (With Instances)
- [ ] Run: `python -m spot_deployer.main list`
- [ ] Verify: Shows "Found X instances in state file"
- [ ] Verify: Shows instance summary by region
- [ ] Verify: Shows "Fetching current instance states from AWS..."
- [ ] Verify: Table shows all instances with current states
- [ ] Verify: Instance IPs are displayed

### 4. SSH Connectivity (Optional)
- [ ] SSH to instance: `ssh -i ~/.ssh/id_ed25519 ubuntu@<IP>`
- [ ] Check uploaded files: `ls -la /opt/uploaded_files/`
- [ ] Check deployment log: `cat /opt/deployment.log`

### 5. Destroy Command
- [ ] Run: `python -m spot_deployer.main destroy`
- [ ] Verify: Shows "Checking local state file for instances..."
- [ ] Verify: Shows "Checking for disconnected Bacalhau nodes..."
- [ ] Verify: Shows "Found X instances in state file"
- [ ] Verify: Shows instance summary by region
- [ ] Verify: Live table shows termination progress
- [ ] Verify: Shows "✓ Complete" for each instance
- [ ] Verify: Summary shows all destroyed
- [ ] Check: `instances.json` is empty

### 6. List Command (After Destroy)
- [ ] Run: `python -m spot_deployer.main list`
- [ ] Verify: Shows "No instances found in state file"
- [ ] Verify: Shows "Checking AWS for orphaned spot instances..."
- [ ] Verify: Lists regions being checked

## Advanced Tests ✅

### 7. Multi-Region Deployment
- [ ] Update config with 2+ regions
- [ ] Run create command
- [ ] Verify: Instances created in all regions
- [ ] Verify: Parallel creation works

### 8. VPC Testing
- [ ] Set `use_dedicated_vpc: true` in config
- [ ] Run create command
- [ ] Verify: "Creating dedicated VPC" message
- [ ] Check AWS Console: Dedicated VPC created
- [ ] Run destroy command
- [ ] Verify: VPC is deleted

### 9. Error Handling Tests

#### Capacity Error
- [ ] Use unavailable instance type (e.g., p4d.24xlarge)
- [ ] Verify: Shows capacity error
- [ ] Verify: No instances created
- [ ] Verify: Clean error message

#### Rate Limiting
- [ ] Create config with 20+ instances
- [ ] Verify: Retry messages appear
- [ ] Verify: Eventually succeeds

#### Network Interruption
- [ ] Start deployment
- [ ] Briefly disconnect network
- [ ] Verify: Retries and recovers

### 10. Nuke Command (CAREFUL!)
- [ ] Create test instances in multiple regions
- [ ] Run: `python -m spot_deployer.main nuke`
- [ ] Verify: Shows scanning progress for all regions
- [ ] Verify: Lists all found instances
- [ ] Verify: Shows termination progress
- [ ] Verify: Updates local state

## Performance Checks ✅

- [ ] Instance creation: ~1-2 minutes
- [ ] SSH availability: ~2-3 minutes
- [ ] File upload: ~30 seconds
- [ ] Total deployment: ~3-5 minutes
- [ ] Destruction: ~1-2 minutes

## AWS Console Verification ✅

### EC2 Dashboard
- [ ] Instances appear with correct tags
- [ ] Security groups created correctly
- [ ] Spot requests show as fulfilled

### VPC Dashboard (if using dedicated)
- [ ] VPC created with correct CIDR
- [ ] Subnets created
- [ ] Internet gateway attached
- [ ] Route tables configured

### CloudTrail
- [ ] API calls logged
- [ ] No unauthorized operations

### Cost Explorer
- [ ] Costs match expectations
- [ ] No unexpected charges

## Log Verification ✅

- [ ] Creation logs: `spot_creation_*.log`
- [ ] Destruction logs: `spot_destroy_*.log`
- [ ] No sensitive data in logs
- [ ] Retry attempts logged

## Cleanup Verification ✅

- [ ] All instances terminated
- [ ] State file empty
- [ ] No orphaned VPCs
- [ ] No orphaned security groups
- [ ] No unexpected AWS resources

## Edge Cases ✅

- [ ] Create with 0 instances (should warn)
- [ ] Destroy with no instances (should handle gracefully)
- [ ] Create in region with no default VPC
- [ ] Destroy instances that were manually terminated

## Notes Section

Use this section to document any issues or observations:

```
Date: ___________
Tester: _________
AWS Account: ____
Issues Found:
-
-
-

Improvements Suggested:
-
-
-
```
