#!/bin/bash
# Test script to verify deployment fix
# Usage: ./test_deployment_fix.sh <instance-ip>

set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <instance-ip>"
    exit 1
fi

INSTANCE_IP=$1
SSH_KEY=$(grep ssh_key_path config.yaml 2>/dev/null | awk '{print $2}' | tr -d '"' || echo "~/.ssh/id_rsa")
USERNAME="ubuntu"

echo "==========================================="
echo "Testing deployment fix on $INSTANCE_IP"
echo "==========================================="
echo ""

# First, upload the deploy_services.py script
echo "1. Uploading deployment script..."
scp -i "$SSH_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    instance/scripts/deploy_services.py "$USERNAME@$INSTANCE_IP:/tmp/deploy_services.py"

echo ""
echo "2. Executing deployment script..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$USERNAME@$INSTANCE_IP" \
    "sudo python3 /tmp/deploy_services.py"

echo ""
echo "3. Checking results..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$USERNAME@$INSTANCE_IP" 'bash -s' << 'ENDSSH'
echo "=== Service Status ==="
for service in bacalhau-startup.service setup-config.service bacalhau.service sensor-generator.service; do
    echo -n "$service: "
    if systemctl is-enabled "$service" 2>/dev/null; then
        echo "enabled"
    else
        echo "not found"
    fi
done

echo ""
echo "=== File Locations ==="
echo "Scripts in /opt/uploaded_files/scripts:"
ls -la /opt/uploaded_files/scripts 2>/dev/null | head -5 || echo "Directory not found"

echo ""
echo "Config files:"
ls -la /opt/uploaded_files/config 2>/dev/null || echo "No config directory"
ls -la /bacalhau_node/config.yaml 2>/dev/null || echo "Bacalhau config not found"
ls -la /opt/sensor/config/sensor-config.yaml 2>/dev/null || echo "Sensor config not found"

echo ""
echo "=== Deployment Log ==="
if [ -f /opt/deployment.log ]; then
    tail -20 /opt/deployment.log
else
    echo "No deployment log found"
fi
ENDSSH

echo ""
echo "==========================================="
echo "Test complete"
echo "==========================================="