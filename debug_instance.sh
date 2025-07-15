#!/bin/bash
# Comprehensive debug script for spot instances

if [ -z "$1" ]; then
    echo "Usage: $0 <instance-ip>"
    exit 1
fi

INSTANCE_IP=$1
SSH_KEY=${SSH_KEY:-~/.ssh/id_rsa}

echo "=== DEBUGGING INSTANCE: $INSTANCE_IP ==="
echo ""

ssh -o "StrictHostKeyChecking=no" -o "UserKnownHostsFile=/dev/null" -i "$SSH_KEY" ubuntu@$INSTANCE_IP 'bash -s' << 'ENDSSH'
echo "=== SYSTEM INFO ==="
echo "Hostname: $(hostname)"
echo "Uptime: $(uptime)"
echo "Current time: $(date)"
echo ""

echo "=== REBOOT HISTORY ==="
last reboot | head -5
echo ""

echo "=== CLOUD-INIT STATUS ==="
cloud-init status --long
echo ""

echo "=== SYSTEMD SERVICE STATUS ==="
echo "--- Service Files ---"
ls -la /etc/systemd/system/*.service | grep -E "(bacalhau|sensor|setup)" || echo "No service files found"
echo ""

echo "--- Service Status ---"
for service in bacalhau-startup setup-config bacalhau sensor-generator; do
    echo "=== $service.service ==="
    systemctl status $service.service --no-pager -l || echo "Service not found"
    echo ""
done

echo "=== STARTUP LOG (/opt/startup.log) ==="
if [ -f /opt/startup.log ]; then
    echo "File size: $(ls -lh /opt/startup.log | awk '{print $5}')"
    echo "--- Full contents ---"
    cat /opt/startup.log
else
    echo "File not found"
fi
echo ""

echo "=== CLOUD-INIT OUTPUT LOG (last 100 lines) ==="
sudo tail -100 /var/log/cloud-init-output.log
echo ""

echo "=== CLOUD-INIT LOG (grep for errors/reboot) ==="
sudo grep -i "error\|fail\|reboot\|shutdown\|power_state" /var/log/cloud-init.log | tail -50
echo ""

echo "=== UPLOADED FILES CHECK ==="
echo "--- Scripts directory ---"
ls -la /opt/uploaded_files/scripts/ 2>/dev/null || echo "Scripts directory not found"
echo ""
echo "--- Config directory ---"
ls -la /opt/uploaded_files/config/ 2>/dev/null || echo "Config directory not found"
echo ""

echo "=== DOCKER STATUS ==="
docker --version 2>&1 || echo "Docker not installed"
docker compose version 2>&1 || echo "Docker compose not installed"
echo "--- Running containers ---"
docker ps -a 2>&1 || echo "Cannot list containers"
echo ""

echo "=== SYSTEMD JOURNAL (last 50 lines for our services) ==="
sudo journalctl -u bacalhau-startup -u setup-config -u bacalhau -u sensor-generator --no-pager -n 50
echo ""

echo "=== CHECK FOR REBOOT MARKERS ==="
echo "--- /tmp/setup_complete ---"
cat /tmp/setup_complete 2>/dev/null || echo "Not found"
echo "--- /tmp/cloud-init-status ---"
cat /tmp/cloud-init-status 2>/dev/null || echo "Not found"
echo ""

echo "=== PROCESS CHECK ==="
ps aux | grep -E "(docker|bacalhau|sensor)" | grep -v grep || echo "No relevant processes found"

ENDSSH