# Comprehensive Test Plan for AWS Spot Instance Deployment Tool

## Overview
This test plan covers all aspects of the AWS spot deployment tool, with each test designed to be executed in a single Claude run. Tests are organized by functional area with clear objectives, steps, and fix guidance.

## Test Categories

### 1. Configuration Validation Tests

#### TEST-001: Missing Configuration File Handling
**Objective**: Verify graceful handling when config.yaml is missing
**Steps**:
```bash
# Rename existing config to backup
mv config.yaml config.yaml.backup
# Try running setup command
uv run -s deploy_spot.py setup
```
**Expected**: Should create default config.yaml with sensible defaults
**Fix if fails**: Add file existence check in SimpleConfig.__init__ with default creation

#### TEST-002: Invalid YAML Syntax Detection
**Objective**: Test error handling for malformed YAML
**Steps**:
```bash
# Create invalid YAML with bad indentation
echo "aws:
  total_instances: 3
    username: ubuntu" > config.yaml
uv run -s deploy_spot.py setup
```
**Expected**: Clear error message about YAML syntax with line number
**Fix if fails**: Enhance yaml.safe_load exception handling with detailed parsing errors

#### TEST-003: SSH Key Validation
**Objective**: Verify SSH key existence checking
**Steps**:
```bash
# Set non-existent SSH key
echo "aws:
  ssh_key_path: /nonexistent/key.pem
  total_instances: 1
regions:
  - us-west-2:
      machine_type: t3.micro" > config.yaml
uv run -s deploy_spot.py create --dry-run
```
**Expected**: Error before attempting deployment
**Fix if fails**: Add SSH key validation in load_config() before deployment

#### TEST-004: Region Limit Validation
**Objective**: Test handling when total_instances < number of regions
**Steps**:
```bash
# Configure 2 instances across 3 regions
echo "aws:
  total_instances: 2
  ssh_key_name: test-key
regions:
  - us-west-2:
      machine_type: t3.micro
  - us-east-1:
      machine_type: t3.micro
  - eu-west-1:
      machine_type: t3.micro" > config.yaml
uv run -s deploy_spot.py create --dry-run
```
**Expected**: Intelligent distribution with warning about unused regions
**Fix if fails**: Enhance _calculate_instance_distribution() with better messaging

### 2. AWS Deployment Tests

#### TEST-005: AMI Auto-Discovery
**Objective**: Verify Ubuntu 22.04 AMI discovery across regions
**Steps**:
```bash
# Clear AMI cache
rm -rf .aws_cache/
# Deploy with auto image selection
echo "aws:
  total_instances: 1
  ssh_key_name: test-key
regions:
  - us-west-2:
      machine_type: t3.micro
      image: auto" > config.yaml
uv run -s deploy_spot.py create --dry-run
```
**Expected**: Successfully discovers latest Ubuntu 22.04 AMI
**Fix if fails**: Update AMI filters in _get_ubuntu_ami() for current patterns

#### TEST-006: VPC/Subnet Discovery
**Objective**: Test VPC/subnet auto-discovery in regions
**Steps**:
```bash
# Deploy without specifying VPC/subnet
uv run -s deploy_spot.py create --region us-west-2 --count 1
```
**Expected**: Automatically finds default VPC and subnet
**Fix if fails**: Enhance _get_vpc_and_subnet() with better fallback logic

#### TEST-007: Spot Price Handling
**Objective**: Verify spot instance pricing logic
**Steps**:
```bash
# Deploy with various instance types
for type in t3.micro t3.small t3.medium; do
  echo "Testing $type spot pricing..."
  uv run -s deploy_spot.py create --dry-run --instance-type $type
done
```
**Expected**: Successfully gets spot prices for each type
**Fix if fails**: Add spot price API error handling with on-demand fallback

### 3. File Upload Tests

#### TEST-008: Script Upload Verification
**Objective**: Ensure all scripts are uploaded correctly
**Steps**:
```bash
# Create test scripts
mkdir -p test_scripts
echo '#!/bin/bash
echo "Test script running"' > test_scripts/test.sh
chmod +x test_scripts/test.sh

# Configure and deploy
echo "aws:
  scripts_directory: test_scripts
  total_instances: 1
  ssh_key_name: test-key
regions:
  - us-west-2:
      machine_type: t3.micro" > config.yaml
uv run -s deploy_spot.py create
```
**Expected**: Scripts uploaded to /opt/uploaded_files/scripts/ with permissions preserved
**Fix if fails**: Check _upload_files_scp() permission preservation logic

#### TEST-009: Large File Upload
**Objective**: Test upload of files >10MB
**Steps**:
```bash
# Create large test file
dd if=/dev/zero of=files/large_test.bin bs=1M count=20
uv run -s deploy_spot.py create --count 1
```
**Expected**: File uploads successfully with progress indication
**Fix if fails**: Add chunked upload or progress callback in paramiko

#### TEST-010: Directory Structure Creation
**Objective**: Verify remote directory creation
**Steps**:
```bash
# Create nested directory structure
mkdir -p files/data/logs/2024
echo "test" > files/data/logs/2024/test.log
uv run -s deploy_spot.py create --count 1
# SSH and verify: ssh ubuntu@<ip> "find /opt/uploaded_files -type f"
```
**Expected**: Full directory structure recreated on remote
**Fix if fails**: Enhance _ensure_remote_directory() for nested paths

### 4. State Management Tests

#### TEST-011: State File Corruption Recovery
**Objective**: Test recovery from corrupted instances.json
**Steps**:
```bash
# Corrupt state file
echo "{invalid json" > instances.json
uv run -s deploy_spot.py list
```
**Expected**: Graceful recovery with warning, creates new valid state
**Fix if fails**: Add JSON validation with backup/recovery in SimpleStateManager

#### TEST-012: State Synchronization
**Objective**: Verify state matches actual AWS resources
**Steps**:
```bash
# Deploy instances
uv run -s deploy_spot.py create --count 2
# Manually terminate one via AWS console
# Run list command
uv run -s deploy_spot.py list --sync
```
**Expected**: Detects terminated instance and updates state
**Fix if fails**: Implement state sync in list_instances() with AWS API

#### TEST-013: Concurrent State Updates
**Objective**: Test thread-safe state management
**Steps**:
```bash
# Deploy to multiple regions simultaneously
echo "aws:
  total_instances: 6
  ssh_key_name: test-key
regions:
  - us-west-2:
      machine_type: t3.micro
  - us-east-1:
      machine_type: t3.micro
  - eu-west-1:
      machine_type: t3.micro" > config.yaml
uv run -s deploy_spot.py create
```
**Expected**: All instances recorded without race conditions
**Fix if fails**: Add file locking in SimpleStateManager.add_instance()

### 5. Error Handling Tests

#### TEST-014: SSH Connection Failure Recovery
**Objective**: Test SSH retry logic
**Steps**:
```bash
# Deploy with immediate SSH attempt (before instance ready)
# Modify SSH timeout to 5 seconds temporarily
uv run -s deploy_spot.py create --count 1 --ssh-timeout 5
```
**Expected**: Retries SSH connection with exponential backoff
**Fix if fails**: Enhance _wait_for_ssh() retry logic with better backoff

#### TEST-015: Region Failure Handling
**Objective**: Test deployment when one region fails
**Steps**:
```bash
# Configure with invalid region
echo "aws:
  total_instances: 3
  ssh_key_name: test-key
regions:
  - us-west-2:
      machine_type: t3.micro
  - invalid-region-1:
      machine_type: t3.micro" > config.yaml
uv run -s deploy_spot.py create
```
**Expected**: Continues with valid regions, reports failure clearly
**Fix if fails**: Improve error aggregation in create_instances()

#### TEST-016: Cleanup After Failure
**Objective**: Verify resources cleaned up after deployment failure
**Steps**:
```bash
# Deploy with script that will fail
echo '#!/bin/bash
exit 1' > instance/scripts/fail.sh
uv run -s deploy_spot.py create --count 1
```
**Expected**: Instance terminated, security group removed
**Fix if fails**: Enhance cleanup in exception handlers

### 6. UI/UX Enhancement Tests

#### TEST-017: Progress Display During Long Operations
**Objective**: Test progress updates during multi-instance deployment
**Steps**:
```bash
# Deploy 10+ instances across regions
echo "aws:
  total_instances: 12
  ssh_key_name: test-key
regions:
  - us-west-2:
      machine_type: t3.micro
  - us-east-1:
      machine_type: t3.micro" > config.yaml
uv run -s deploy_spot.py create
```
**Expected**: Real-time progress with instance-specific status
**Fix if fails**: Add rich.Progress with multiple progress bars

#### TEST-018: Table Formatting Edge Cases
**Objective**: Test table display with long values
**Steps**:
```bash
# Create instance with long name tag
uv run -s deploy_spot.py create --count 1 --tag "VeryLongInstanceNameThatMightBreakTableFormatting123456789"
```
**Expected**: Table adjusts column widths appropriately
**Fix if fails**: Set max column widths in Rich table configuration

#### TEST-019: Error Message Clarity
**Objective**: Test error messages for various failure scenarios
**Steps**:
```bash
# Test multiple error scenarios
# 1. Invalid AWS credentials
unset AWS_PROFILE
uv run -s deploy_spot.py create --count 1
# 2. Insufficient permissions
# 3. Resource limits exceeded
```
**Expected**: Clear, actionable error messages with fix suggestions
**Fix if fails**: Create error message templates with solutions

### 7. Node Identity Tests

#### TEST-020: Identity Generation Determinism
**Objective**: Verify same instance ID produces same identity
**Steps**:
```bash
# Test identity generation
INSTANCE_ID=i-1234567890abcdef0 python3 instance/scripts/generate_node_identity.py
# Run again
INSTANCE_ID=i-1234567890abcdef0 python3 instance/scripts/generate_node_identity.py
# Compare outputs
```
**Expected**: Identical JSON output both times
**Fix if fails**: Remove any random elements from NodeIdentityGenerator

#### TEST-021: Identity File Permissions
**Objective**: Verify identity file has correct permissions
**Steps**:
```bash
# Deploy and check permissions
uv run -s deploy_spot.py create --count 1
# SSH and check: ssh ubuntu@<ip> "ls -la /opt/sensor/config/node_identity.json"
```
**Expected**: File readable by services, not world-readable (644)
**Fix if fails**: Set explicit permissions in generate_node_identity.py

#### TEST-022: GPS Coordinate Validation
**Objective**: Test GPS coordinate generation stays within bounds
**Steps**:
```bash
# Generate 100 identities and validate coordinates
for i in {1..100}; do
  INSTANCE_ID=i-test$i python3 instance/scripts/generate_node_identity.py
done
# Verify all coordinates are valid lat/long
```
**Expected**: All coordinates within valid GPS ranges
**Fix if fails**: Add coordinate validation in _add_coordinate_noise()

### 8. Performance Tests

#### TEST-023: Startup Time Benchmark
**Objective**: Verify <1 second startup time
**Steps**:
```bash
# Time the help command
time uv run -s deploy_spot.py help
# Time config loading
time python3 -c "from deploy_spot import SimpleConfig; SimpleConfig()"
```
**Expected**: Help completes in <0.2s, config load <0.1s
**Fix if fails**: Profile code, optimize imports

#### TEST-024: Concurrent Deployment Performance
**Objective**: Test deployment speed with many instances
**Steps**:
```bash
# Time deployment of 20 instances
time uv run -s deploy_spot.py create --count 20
```
**Expected**: Parallel deployment, <5 min for 20 instances
**Fix if fails**: Increase thread pool size, optimize API calls

#### TEST-025: Memory Usage
**Objective**: Verify reasonable memory usage
**Steps**:
```bash
# Monitor memory during large deployment
/usr/bin/time -v uv run -s deploy_spot.py create --count 50
```
**Expected**: Memory usage <100MB
**Fix if fails**: Stream file uploads, reduce state copies

### 9. Cleanup Tests

#### TEST-026: Complete Cleanup Verification
**Objective**: Ensure destroy removes all resources
**Steps**:
```bash
# Deploy full infrastructure
uv run -s deploy_spot.py create --count 5
# Note security group IDs
# Destroy
uv run -s deploy_spot.py destroy
# Verify via AWS CLI
aws ec2 describe-instances --filters "Name=tag:Name,Values=spot-demo-*"
```
**Expected**: No instances, security groups removed
**Fix if fails**: Add resource tagging and comprehensive cleanup

#### TEST-027: VPC Cleanup Safety
**Objective**: Test VPC cleanup doesn't affect other resources
**Steps**:
```bash
# Run VPC cleanup in dry-run mode
uv run -s delete_vpcs.py --dry-run
# Verify it only targets deployment-created VPCs
```
**Expected**: Only lists VPCs with deployment tags
**Fix if fails**: Add better VPC filtering by tags

#### TEST-028: Partial Cleanup
**Objective**: Test destroying specific instances
**Steps**:
```bash
# Deploy 3 instances
uv run -s deploy_spot.py create --count 3
# Destroy only in one region
uv run -s deploy_spot.py destroy --region us-west-2
```
**Expected**: Only specified region's instances destroyed
**Fix if fails**: Add region filtering to destroy_instances()

### 10. Integration Tests

#### TEST-029: End-to-End Deployment
**Objective**: Full deployment with all features
**Steps**:
```bash
# Complete deployment test
echo "aws:
  total_instances: 3
  username: ubuntu
  ssh_key_name: test-key
  files_directory: files
  scripts_directory: instance/scripts
regions:
  - us-west-2:
      machine_type: t3.small
      image: auto" > config.yaml

# Add test files
echo "test data" > files/test.txt
# Deploy
uv run -s deploy_spot.py create
# Verify services running
uv run -s deploy_spot.py list --check-health
```
**Expected**: All instances running, services active, files uploaded
**Fix if fails**: Debug each phase, check logs at /opt/startup.log

#### TEST-030: Service Health Verification
**Objective**: Verify Bacalhau services start correctly
**Steps**:
```bash
# Deploy and wait for services
uv run -s deploy_spot.py create --count 1
sleep 120  # Wait for services
# Check service status
ssh ubuntu@<ip> "sudo systemctl status bacalhau-startup.service"
ssh ubuntu@<ip> "docker ps"
```
**Expected**: Services active, Docker containers running
**Fix if fails**: Check startup.py error handling, Docker installation

### 11. Edge Case Tests

#### TEST-031: Unicode Handling
**Objective**: Test Unicode in filenames and content
**Steps**:
```bash
# Create files with Unicode names
echo "测试" > files/测试文件.txt
echo "🚀 Emoji test" > files/emoji.txt
uv run -s deploy_spot.py create --count 1
```
**Expected**: Files uploaded correctly with names preserved
**Fix if fails**: Ensure UTF-8 encoding throughout

#### TEST-032: Extremely Long Filenames
**Objective**: Test filename length limits
**Steps**:
```bash
# Create file with 255 character name
touch files/$(python3 -c "print('a' * 250 + '.txt')")
uv run -s deploy_spot.py create --count 1
```
**Expected**: Handles gracefully, truncates if needed
**Fix if fails**: Add filename validation in upload logic

#### TEST-033: Network Interruption Recovery
**Objective**: Test handling of network failures during deployment
**Steps**:
```bash
# Start deployment
uv run -s deploy_spot.py create --count 5 &
# Simulate network interruption (disconnect WiFi briefly)
# Reconnect and check state
```
**Expected**: Graceful failure with partial state saved
**Fix if fails**: Add connection retry logic, checkpoint saves

### 12. Security Tests

#### TEST-034: SSH Key Permission Validation
**Objective**: Verify SSH key permission checks
**Steps**:
```bash
# Create SSH key with wrong permissions
ssh-keygen -f test_key -N ""
chmod 644 test_key
echo "aws:
  ssh_key_path: test_key
  total_instances: 1" > config.yaml
uv run -s deploy_spot.py create
```
**Expected**: Refuses to use key with incorrect permissions
**Fix if fails**: Add permission check for 600/400 in SSH code

#### TEST-035: Security Group Rule Validation
**Objective**: Verify minimal security group rules
**Steps**:
```bash
# Deploy and check security group
uv run -s deploy_spot.py create --count 1
# Get security group rules via AWS CLI
```
**Expected**: Only ports 22 and 4222 open, source restrictions
**Fix if fails**: Review security group creation in _create_security_group()

## Test Execution Guidelines

1. **Before Each Test**: 
   - Backup config.yaml
   - Clear instances.json
   - Note AWS resource state

2. **After Each Test**:
   - Run cleanup if needed
   - Restore original config
   - Verify no orphaned resources

3. **Logging**:
   - Capture all output
   - Note any warnings
   - Document actual vs expected

4. **Fix Priority**:
   - P0: Data loss or security issues
   - P1: Deployment failures
   - P2: UX/UI issues
   - P3: Performance optimizations

## Automated Test Script

Create `run_all_tests.sh`:
```bash
#!/bin/bash
# Automated test runner
LOGDIR="test_logs_$(date +%Y%m%d_%H%M%S)"
mkdir -p $LOGDIR

run_test() {
    TEST_ID=$1
    TEST_NAME=$2
    echo "Running $TEST_ID: $TEST_NAME"
    # Test-specific commands here
    # Log output to $LOGDIR/$TEST_ID.log
}

# Run all tests
run_test "TEST-001" "Missing Configuration File Handling"
# ... continue for all tests

echo "Test run complete. Logs in $LOGDIR/"
```