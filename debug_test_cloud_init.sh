#!/bin/bash
# Test 1: Cloud-Init Status and Completion
# Usage: ./debug_test_cloud_init.sh <instance-ip>

set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <instance-ip>"
    exit 1
fi

INSTANCE_IP=$1
SSH_KEY=$(grep ssh_key_path config.yaml 2>/dev/null | awk '{print $2}' | tr -d '"' || echo "~/.ssh/id_rsa")
USERNAME="ubuntu"

echo "=========================================="
echo "Cloud-Init Debug Test for $INSTANCE_IP"
echo "=========================================="
echo ""

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$USERNAME@$INSTANCE_IP" 'bash -s' << 'ENDSSH'

# Function to check status with color
check_status() {
    if [ $1 -eq 0 ]; then
        echo -e "✅ $2"
    else
        echo -e "❌ $2"
    fi
}

echo "1. Cloud-Init Status Check"
echo "--------------------------"
status=$(sudo cloud-init status --wait 2>&1)
if echo "$status" | grep -q "status: done"; then
    check_status 0 "Cloud-init completed successfully"
elif echo "$status" | grep -q "status: running"; then
    echo "⏳ Cloud-init still running..."
else
    check_status 1 "Cloud-init failed or in error state"
fi
echo "Full status: $status"
echo ""

echo "2. Cloud-Init Progress File"
echo "---------------------------"
if [ -f /tmp/cloud-init-status ]; then
    check_status 0 "Progress file exists"
    echo "Contents:"
    cat /tmp/cloud-init-status
else
    check_status 1 "Progress file missing"
fi
echo ""

echo "3. Cloud-Init Errors"
echo "--------------------"
error_count=$(sudo grep -i error /var/log/cloud-init-output.log 2>/dev/null | grep -v "no error" | wc -l)
if [ $error_count -eq 0 ]; then
    check_status 0 "No errors found in cloud-init log"
else
    check_status 1 "Found $error_count errors in cloud-init log"
    echo "First 10 errors:"
    sudo grep -i error /var/log/cloud-init-output.log | grep -v "no error" | head -10
fi
echo ""

echo "4. Package Installation Status"
echo "------------------------------"
# Check key packages
packages=("docker-ce" "python3" "curl" "git")
failed_packages=0
for pkg in "${packages[@]}"; do
    if dpkg -l | grep -q "^ii.*$pkg"; then
        echo "✅ $pkg installed"
    else
        echo "❌ $pkg NOT installed"
        ((failed_packages++))
    fi
done
check_status $failed_packages "All packages installed"
echo ""

echo "5. Cloud-Init Timing"
echo "--------------------"
# Check for wait loop messages
if sudo grep -q "Waiting for service files" /var/log/cloud-init-output.log; then
    echo "⏱️  Cloud-init waited for service files"
    wait_time=$(sudo grep "Waiting for service files" /var/log/cloud-init-output.log | wc -l)
    echo "   Waited approximately $wait_time seconds"
else
    echo "ℹ️  No wait loop detected"
fi
echo ""

echo "6. System Information"
echo "---------------------"
echo "Uptime: $(uptime)"
echo "Kernel: $(uname -r)"
echo "Instance ID: $(ec2-metadata --instance-id 2>/dev/null | cut -d' ' -f2 || echo "Unknown")"
echo ""

echo "7. Cloud-Init Final Status"
echo "--------------------------"
sudo cloud-init analyze show
echo ""

echo "Summary"
echo "-------"
if [ $error_count -eq 0 ] && [ $failed_packages -eq 0 ]; then
    echo "✅ Cloud-init appears to have completed successfully"
else
    echo "❌ Cloud-init encountered issues - check logs above"
fi

ENDSSH