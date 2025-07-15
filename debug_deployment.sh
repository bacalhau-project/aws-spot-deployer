#!/bin/bash
# Comprehensive deployment debugging script
# Usage: ./debug_deployment.sh <instance-ip>

set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <instance-ip>"
    echo "Example: $0 54.123.45.67"
    exit 1
fi

INSTANCE_IP=$1
SSH_KEY=$(grep ssh_key_path config.yaml | awk '{print $2}' | tr -d '"')
USERNAME=$(grep username config.yaml | awk '{print $2}' | tr -d '"' || echo "ubuntu")

echo "==================================================="
echo "Deployment Debug Report for $INSTANCE_IP"
echo "==================================================="
echo "Date: $(date)"
echo "SSH Key: $SSH_KEY"
echo "Username: $USERNAME"
echo ""

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$USERNAME@$INSTANCE_IP" 'bash -s' << 'ENDSSH'
echo "=== SYSTEM INFO ==="
echo "Hostname: $(hostname)"
echo "Uptime: $(uptime)"
echo "Instance ID: $(curl -s http://169.254.169.254/latest/meta-data/instance-id 2>/dev/null || echo "N/A")"
echo ""

echo "=== FILE LOCATIONS CHECK ==="
echo "--- /opt/uploaded_files/scripts ---"
ls -la /opt/uploaded_files/scripts/ 2>/dev/null || echo "Directory not found"
echo ""
echo "--- /tmp/uploaded_files/scripts ---"
ls -la /tmp/uploaded_files/scripts/ 2>/dev/null || echo "Directory not found"
echo ""
echo "--- /tmp/exs ---"
ls -la /tmp/exs/ 2>/dev/null || echo "Directory not found"
echo ""
echo "--- /opt/uploaded_files/config ---"
ls -la /opt/uploaded_files/config/ 2>/dev/null || echo "Directory not found"
echo ""

echo "=== CHECKING FOR STARTUP SCRIPTS ==="
echo "startup.py locations:"
find / -name "startup.py" -type f 2>/dev/null | grep -v proc || echo "Not found"
echo ""
echo "simple-startup.py locations:"
find / -name "simple-startup.py" -type f 2>/dev/null | grep -v proc || echo "Not found"
echo ""

echo "=== SYSTEMD SERVICE STATUS ==="
echo "--- bacalhau-startup.service ---"
sudo systemctl status --no-pager -l bacalhau-startup.service 2>&1 || echo "Service not found"
echo ""
echo "--- setup-config.service ---"
sudo systemctl status --no-pager -l setup-config.service 2>&1 || echo "Service not found"
echo ""
echo "--- bacalhau.service ---"
sudo systemctl status --no-pager -l bacalhau.service 2>&1 || echo "Service not found"
echo ""
echo "--- sensor-generator.service ---"
sudo systemctl status --no-pager -l sensor-generator.service 2>&1 || echo "Service not found"
echo ""

echo "=== SERVICE LOGS (Last 20 lines) ==="
echo "--- bacalhau-startup.service ---"
sudo journalctl -u bacalhau-startup.service -n 20 --no-pager 2>&1 || echo "No logs"
echo ""
echo "--- setup-config.service ---"
sudo journalctl -u setup-config.service -n 20 --no-pager 2>&1 || echo "No logs"
echo ""

echo "=== STARTUP LOG FILE ==="
if [ -f /opt/startup.log ]; then
    echo "--- Last 30 lines of /opt/startup.log ---"
    sudo tail -30 /opt/startup.log
else
    echo "/opt/startup.log not found"
fi
echo ""

echo "=== CLOUD-INIT STATUS ==="
cloud-init status --long 2>&1 || echo "cloud-init command not available"
echo ""

echo "=== CLOUD-INIT LOG (Last 50 lines) ==="
sudo tail -50 /var/log/cloud-init-output.log 2>&1 || echo "Log not found"
echo ""

echo "=== DOCKER STATUS ==="
docker --version 2>&1 || echo "Docker not installed"
sudo systemctl is-active docker 2>&1 || echo "Docker service not active"
echo ""
echo "Docker containers:"
docker ps -a 2>&1 || echo "No containers or Docker not available"
echo ""

echo "=== DIRECTORY STRUCTURE ==="
echo "--- /bacalhau_node ---"
ls -la /bacalhau_node/ 2>/dev/null || echo "Directory not found"
echo ""
echo "--- /bacalhau_data ---"
ls -la /bacalhau_data/ 2>/dev/null || echo "Directory not found"
echo ""
echo "--- /opt/sensor ---"
ls -la /opt/sensor/ 2>/dev/null || echo "Directory not found"
ls -la /opt/sensor/config/ 2>/dev/null || echo "Config directory not found"
echo ""

echo "=== NODE IDENTITY CHECK ==="
if [ -f /opt/sensor/config/node_identity.json ]; then
    echo "Node identity found:"
    cat /opt/sensor/config/node_identity.json | jq . 2>/dev/null || cat /opt/sensor/config/node_identity.json
else
    echo "Node identity file not found"
fi
echo ""

echo "=== CONFIGURATION FILES ==="
echo "--- /bacalhau_node/config.yaml ---"
if [ -f /bacalhau_node/config.yaml ]; then
    head -20 /bacalhau_node/config.yaml
else
    echo "File not found"
fi
echo ""
echo "--- /opt/sensor/config/sensor-config.yaml ---"
if [ -f /opt/sensor/config/sensor-config.yaml ]; then
    cat /opt/sensor/config/sensor-config.yaml
else
    echo "File not found"
fi
echo ""

echo "=== RECENT SYSTEM ERRORS ==="
sudo journalctl -p err -n 20 --no-pager 2>&1 || echo "No errors in journal"
echo ""

echo "=== PROCESS TREE ==="
ps auxf | head -50
echo ""

echo "=== COMPLETION MARKER ==="
if [ -f /tmp/startup_complete ]; then
    echo "Startup completion marker found:"
    cat /tmp/startup_complete
else
    echo "Startup completion marker not found"
fi

echo ""
echo "==================================================="
echo "Debug report complete"
echo "==================================================="
ENDSSH