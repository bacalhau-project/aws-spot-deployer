# Testing Guide for Spot Deployer

This guide explains how to safely test Spot Deployer with real AWS resources.

## Prerequisites

1. **AWS Account**: You need an active AWS account
2. **AWS Credentials**: Configure AWS credentials using one of:
   - AWS SSO: `aws sso login`
   - AWS Profile: `export AWS_PROFILE=your-profile`
   - IAM Keys: `export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=...`
3. **SSH Keys**: Generate if not exists:
   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""
   ```

## Safety First! 🚨

**IMPORTANT**: Always test in a controlled environment to avoid unexpected costs.

### Recommended Safety Measures

1. **Use a Test AWS Account**: If possible, use a separate AWS account for testing
2. **Set Spending Alerts**: Configure AWS billing alerts before testing
3. **Start Small**: Test with minimal instances (1-2) first
4. **Choose Cheap Regions**: Start with regions that typically have lower spot prices
5. **Monitor Costs**: Check AWS Cost Explorer after testing

## Step-by-Step Testing Process

### 1. Create a Test Configuration

Create a minimal test configuration file:

```bash
cat > test-config.yaml << EOF
aws:
  total_instances: 2  # Start with just 2 instances
  username: ubuntu
  public_ssh_key_path: ~/.ssh/id_ed25519.pub
  private_ssh_key_path: ~/.ssh/id_ed25519
  files_directory: files
  scripts_directory: instance/scripts
  use_dedicated_vpc: false  # Use default VPC for testing
  instance_storage_gb: 8    # Minimal storage
  tags:
    Environment: Testing
    Purpose: SpotDeployerTest
regions:
  - us-east-2:  # Usually has good spot availability
      machine_type: t3.micro  # Cheapest instance type
      image: auto
EOF
```

### 2. Prepare Test Files

Create minimal test files:

```bash
mkdir -p files
echo "test content" > files/test.txt
```

If testing Bacalhau integration:
```bash
echo "nats://test-orchestrator.example.com:4222" > files/orchestrator_endpoint
echo "test-token-12345" > files/orchestrator_token
```

### 3. Test Commands in Order

#### A. Test List Command (Safe - Read Only)
```bash
python -m spot_deployer.main list
```
Expected: "No instances found in state file."

#### B. Test Create Command
```bash
# First, do a dry run by checking the configuration
python -m spot_deployer.main create --config test-config.yaml
```

Watch for:
- Progress messages showing VPC/subnet discovery
- Instance creation progress
- SSH key injection
- File upload progress

Expected timeline:
- Instance creation: 1-2 minutes
- SSH availability: 2-3 minutes
- Total deployment: 3-5 minutes

#### C. Test List Command Again
```bash
python -m spot_deployer.main list
```

Expected: Should show your 2 test instances with IPs and states

#### D. Verify Instance Access (Optional)
```bash
# Get instance IP from list output
ssh -i ~/.ssh/id_ed25519 ubuntu@<instance-ip>

# Check uploaded files
ls -la /opt/uploaded_files/
```

#### E. Test Destroy Command
```bash
python -m spot_deployer.main destroy
```

Watch for:
- Instance termination progress
- VPC cleanup (if using dedicated VPC)
- State file cleanup

#### F. Verify Cleanup
```bash
python -m spot_deployer.main list
```
Expected: "No instances found in state file."

### 4. Test Error Scenarios

#### Test Capacity Issues
Create a config requesting unavailable instance types:
```yaml
regions:
  - us-east-1:
      machine_type: p4d.24xlarge  # Likely unavailable
      image: auto
```

Expected: Graceful failure with clear error message

#### Test Rate Limiting
```yaml
aws:
  total_instances: 50  # Large number to trigger rate limits
```

Expected: Retry logic should handle rate limiting

#### Test Network Failures
1. Start a deployment
2. Disconnect network briefly
3. Reconnect

Expected: Retry logic should recover

### 5. Test Nuke Command (Use with Extreme Caution!)

**WARNING**: This terminates ALL spot instances in ALL regions!

```bash
# First, check what would be affected
python -m spot_deployer.main nuke
```

The command will show all instances before terminating.

## Monitoring During Tests

### Check AWS Console
1. **EC2 Dashboard**: Monitor instance creation/termination
2. **VPC Dashboard**: Check VPC/subnet creation (if using dedicated)
3. **CloudTrail**: Audit all API calls
4. **Cost Explorer**: Monitor spending

### Check Logs
```bash
# Deployment logs
ls -la spot_creation_*.log
tail -f spot_creation_*.log

# Destruction logs
ls -la spot_destroy_*.log
```

### Check State File
```bash
cat instances.json | jq .
```

## Cost Estimation

Typical test costs (us-east-2, 2x t3.micro for 1 hour):
- Spot instances: ~$0.01-0.02
- EBS storage (8GB): ~$0.01
- Data transfer: ~$0.01
- **Total: ~$0.03-0.05**

## Troubleshooting

### SSH Connection Fails
1. Check security group allows port 22
2. Verify instance has public IP
3. Check SSH key permissions: `chmod 600 ~/.ssh/id_ed25519`

### Instance Creation Fails
1. Check AWS credentials: `aws sts get-caller-identity`
2. Verify spot service-linked role exists
3. Try different region/instance type

### File Upload Fails
1. Check instance is fully booted (cloud-init complete)
2. Verify SSH connectivity first
3. Check disk space on instance

## Cleanup Checklist

After testing, ensure:
- [ ] All instances terminated
- [ ] State file empty or removed
- [ ] No orphaned VPCs (if using dedicated)
- [ ] No unexpected charges in billing

## Automated Test Script

For repeated testing, create a test script:

```bash
#!/bin/bash
set -e

echo "Starting Spot Deployer test..."

# Configuration
CONFIG="test-config.yaml"
INSTANCES=2

echo "1. Checking initial state..."
python -m spot_deployer.main list

echo "2. Creating $INSTANCES instances..."
python -m spot_deployer.main create --config $CONFIG

echo "3. Waiting for deployment to complete..."
sleep 300  # 5 minutes

echo "4. Listing instances..."
python -m spot_deployer.main list

echo "5. Destroying instances..."
python -m spot_deployer.main destroy

echo "6. Verifying cleanup..."
python -m spot_deployer.main list

echo "Test completed successfully!"
```

## Integration with CI/CD

For automated testing in CI/CD:

1. Use AWS IAM roles for authentication
2. Create temporary test configurations
3. Set timeouts for all operations
4. Always run destroy in finally blocks
5. Monitor costs with budget alerts

## Next Steps

After successful testing:
1. Gradually increase instance counts
2. Test in multiple regions
3. Test different instance types
4. Test VPC creation/deletion
5. Test with real Bacalhau credentials
