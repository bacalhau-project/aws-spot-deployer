#!/bin/bash
# Quick debug script for spot instances
# Usage: ./debug_instance.sh <instance-ip>

IP=$1
if [ -z "$IP" ]; then
    echo "Usage: $0 <instance-ip>"
    exit 1
fi

SSH="ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i ~/.ssh/id_ed25519 ubuntu@$IP"

echo "=== Cloud-init Status ==="
$SSH "cloud-init status" 2>/dev/null || echo "Failed to connect"

echo -e "\n=== Watcher Process ==="
$SSH "ps aux | grep watch-for-deployment | grep -v grep" 2>/dev/null || echo "No watcher found"

echo -e "\n=== Uploaded Files ==="
$SSH "find /tmp/uploaded_files -type f 2>/dev/null | wc -l" || echo "0"

echo -e "\n=== Deployment Logs ==="
$SSH "tail -20 /home/ubuntu/deployment.log 2>/dev/null || echo 'No deployment log found'"

echo -e "\n=== Startup Log ==="
$SSH "tail -20 /opt/startup.log 2>/dev/null || echo 'No startup log found'"

echo -e "\n=== Systemd Services ==="
$SSH "systemctl list-unit-files | grep -E '(bacalhau|sensor)'" 2>/dev/null || echo "No services found"

echo -e "\n=== Docker Status ==="
$SSH "docker ps 2>/dev/null || echo 'Docker not running or not installed'"

echo -e "\n=== Directory Structure ==="
$SSH "ls -la /opt/ 2>/dev/null | grep -E '(uploaded_files|sensor|deployment)'" || echo "Directories not found"
$SSH "ls -la /bacalhau_node /bacalhau_data 2>/dev/null || echo 'Bacalhau dirs not found'"

echo -e "\n=== Node Identity ==="
$SSH "cat /opt/sensor/config/node_identity.json 2>/dev/null | jq -c '{sensor_id, location: {city: .location.city, state: .location.state}}' || echo 'No identity generated'"

echo -e "\n=== Reboot Status ==="
$SSH "shutdown --show 2>/dev/null || echo 'No reboot scheduled'"