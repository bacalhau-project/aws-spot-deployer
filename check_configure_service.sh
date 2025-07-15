#!/bin/bash
# Check the configure-services.service status
# Usage: ./check_configure_service.sh <instance-ip>

set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <instance-ip>"
    exit 1
fi

INSTANCE_IP=$1
SSH_KEY=$(grep ssh_key_path config.yaml 2>/dev/null | awk '{print $2}' | tr -d '"' || echo "~/.ssh/id_rsa")
USERNAME="ubuntu"

echo "=========================================="
echo "Configure Services Check for $INSTANCE_IP"
echo "=========================================="
echo ""

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$USERNAME@$INSTANCE_IP" 'bash -s' << 'ENDSSH'

echo "1. Checking if configure-services.service exists"
echo "-------------------------------------------------"
if [ -f /etc/systemd/system/configure-services.service ]; then
    echo "✓ Service file exists"
    echo ""
    echo "Content:"
    cat /etc/systemd/system/configure-services.service
    echo ""
else
    echo "✗ Service file NOT FOUND"
fi

echo ""
echo "2. Checking if configure-services.sh exists"
echo "--------------------------------------------"
if [ -f /opt/configure-services.sh ]; then
    echo "✓ Script exists"
    ls -la /opt/configure-services.sh
    echo ""
    echo "First 30 lines of script:"
    head -30 /opt/configure-services.sh
else
    echo "✗ Script NOT FOUND"
fi

echo ""
echo "3. Service status"
echo "-----------------"
sudo systemctl status configure-services.service --no-pager || echo "Service not found"

echo ""
echo "4. Service logs"
echo "---------------"
sudo journalctl -u configure-services.service -n 50 --no-pager || echo "No logs"

echo ""
echo "5. Attempting to start service manually"
echo "---------------------------------------"
sudo systemctl daemon-reload
sudo systemctl start configure-services.service || echo "Failed to start"

echo ""
echo "6. Check results after manual start"
echo "-----------------------------------"
echo "Services in systemd:"
ls -la /etc/systemd/system/*.service | grep -E "(bacalhau|sensor|setup|configure)" || echo "No services"

echo ""
echo "Files in /opt/uploaded_files/scripts:"
ls -la /opt/uploaded_files/scripts/ || echo "Empty or missing"

ENDSSH