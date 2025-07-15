#!/bin/bash
# Quick fix script to update and run deployment on existing instance
# Usage: ./quick_fix_deploy.sh <instance-ip>

set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <instance-ip>"
    exit 1
fi

INSTANCE_IP=$1
SSH_KEY=$(grep ssh_key_path config.yaml 2>/dev/null | awk '{print $2}' | tr -d '"' || echo "~/.ssh/id_rsa")
USERNAME="ubuntu"

echo "Applying quick fix to $INSTANCE_IP..."

# Upload the updated deployment script
scp -i "$SSH_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    instance/scripts/deploy_services.py "$USERNAME@$INSTANCE_IP:/tmp/deploy_services.py"

# Upload the fixed service file
scp -i "$SSH_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    instance/scripts/bacalhau-startup.service "$USERNAME@$INSTANCE_IP:/tmp/bacalhau-startup.service"

# Apply the fix
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$USERNAME@$INSTANCE_IP" 'bash -s' << 'ENDSSH'
# Copy the fixed service file
sudo cp /tmp/bacalhau-startup.service /tmp/exs/bacalhau-startup.service
sudo cp /tmp/bacalhau-startup.service /tmp/uploaded_files/scripts/bacalhau-startup.service

# Run the deployment script
sudo python3 /tmp/deploy_services.py

echo ""
echo "Fix applied. Checking status..."
echo ""

# Check service status
for service in bacalhau-startup.service setup-config.service bacalhau.service sensor-generator.service; do
    echo -n "$service: "
    if systemctl is-enabled "$service" 2>/dev/null; then
        echo "enabled ($(systemctl is-active "$service" 2>/dev/null || echo 'inactive'))"
    else
        echo "not found"
    fi
done
ENDSSH

echo ""
echo "Fix complete. System will reboot in ~1 minute."