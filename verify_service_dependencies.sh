#!/bin/bash
# Check service dependencies on remote instance
# Usage: ./verify_service_dependencies.sh <instance-ip>

set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <instance-ip>"
    exit 1
fi

INSTANCE_IP=$1
SSH_KEY=$(grep ssh_key_path config.yaml 2>/dev/null | awk '{print $2}' | tr -d '"' || echo "~/.ssh/id_rsa")
USERNAME="ubuntu"

echo "==========================================="
echo "Checking service dependencies on $INSTANCE_IP"
echo "==========================================="
echo ""

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$USERNAME@$INSTANCE_IP" 'bash -s' << 'ENDSSH'
echo "=== Service Files ==="
for service in bacalhau-startup.service setup-config.service bacalhau.service sensor-generator.service; do
    echo ""
    echo "--- $service ---"
    if [ -f "/etc/systemd/system/$service" ]; then
        echo "Location: /etc/systemd/system/$service"
        grep -E "^(After=|Requires=|Before=|Wants=)" "/etc/systemd/system/$service" || echo "No dependencies found"
    else
        echo "Not installed in systemd"
        if [ -f "/tmp/exs/$service" ]; then
            echo "Found in /tmp/exs/$service"
            grep -E "^(After=|Requires=|Before=|Wants=)" "/tmp/exs/$service" || echo "No dependencies found"
        fi
    fi
done

echo ""
echo "=== Checking for configure-services references ==="
grep -r "configure-services" /etc/systemd/system/*.service 2>/dev/null || echo "No references found in systemd"
echo ""
grep -r "configure-services" /tmp/exs/*.service 2>/dev/null || echo "No references found in /tmp/exs"

echo ""
echo "=== Systemctl Status ==="
for service in configure-services.service bacalhau-startup.service setup-config.service; do
    echo ""
    echo "--- $service ---"
    sudo systemctl status "$service" --no-pager 2>&1 | head -10 || echo "Service not found"
done
ENDSSH