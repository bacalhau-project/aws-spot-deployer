#!/bin/bash

# Quick status check for all instances
echo "Checking instance status..."
echo ""

# List of IPs from your instances
IPS=(
    "3.145.2.150"      # us-east-2
    "3.98.108.50"      # ca-central-1
    "52.31.54.4"       # eu-west-1
    "3.70.246.75"      # eu-central-1
    "57.182.252.84"    # ap-northeast-1
    "13.61.100.145"    # eu-north-1
    "52.67.108.9"      # sa-east-1
    "52.76.83.231"     # ap-southeast-1
)

for IP in "${IPS[@]}"; do
    echo "=== Checking $IP ==="
    
    # Check if SSH is available
    if timeout 3 ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=2 ubuntu@$IP "echo 'SSH OK'" 2>/dev/null; then
        # Get quick status
        ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ubuntu@$IP "
            echo 'Uptime:' && uptime
            echo -e '\nDocker:' && docker --version 2>&1 || echo 'Not installed'
            echo -e '\nDocker Compose:' && docker compose version 2>&1 || echo 'Not available'
            echo -e '\nServices:' && sudo systemctl is-active bacalhau-startup setup-deployment 2>&1
            echo -e '\nContainers:' && docker ps --format 'table {{.Names}}\t{{.Status}}' 2>&1 || echo 'None'
        " 2>/dev/null
    else
        echo "SSH not available yet (instance may be rebooting)"
    fi
    echo ""
done