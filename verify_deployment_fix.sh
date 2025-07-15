#!/bin/bash
# Verify that the deployment fixes are working
# Usage: ./verify_deployment_fix.sh <instance-ip>

set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <instance-ip>"
    exit 1
fi

INSTANCE_IP=$1
SSH_KEY=$(grep ssh_key_path config.yaml 2>/dev/null | awk '{print $2}' | tr -d '"' || echo "~/.ssh/id_rsa")
USERNAME="ubuntu"

echo "=========================================="
echo "Verifying Deployment Fix on $INSTANCE_IP"
echo "=========================================="
echo ""

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$USERNAME@$INSTANCE_IP" 'bash -s' << 'ENDSSH'

echo "1. Checking configure-services.service"
echo "--------------------------------------"
if [ -f /etc/systemd/system/configure-services.service ]; then
    echo "✓ Service file exists"
    echo "Content:"
    cat /etc/systemd/system/configure-services.service
    echo ""
    echo "Status:"
    sudo systemctl status configure-services.service --no-pager || true
else
    echo "✗ Service file missing"
fi
echo ""

echo "2. Checking configure-services.sh script"
echo "----------------------------------------"
if [ -f /opt/configure-services.sh ]; then
    echo "✓ Script exists"
    echo "Permissions: $(ls -la /opt/configure-services.sh)"
    echo "First 20 lines:"
    head -20 /opt/configure-services.sh
else
    echo "✗ Script missing"
fi
echo ""

echo "3. Attempting to run configure-services manually"
echo "------------------------------------------------"
if [ -f /opt/configure-services.sh ]; then
    echo "Running script..."
    sudo bash /opt/configure-services.sh
    echo "Script completed with exit code: $?"
else
    echo "Cannot run - script not found"
fi
echo ""

echo "4. Checking results"
echo "-------------------"
echo "Service files in systemd:"
ls -la /etc/systemd/system/ | grep -E "(bacalhau|sensor|setup)" || echo "No services found"
echo ""

echo "Scripts in /opt/uploaded_files/scripts:"
ls -la /opt/uploaded_files/scripts/ 2>/dev/null || echo "Directory not found or empty"
echo ""

echo "5. Service status check"
echo "-----------------------"
for svc in bacalhau-startup setup-config bacalhau sensor-generator; do
    echo -n "$svc: "
    systemctl is-enabled $svc.service 2>/dev/null || echo "not found"
done

ENDSSH