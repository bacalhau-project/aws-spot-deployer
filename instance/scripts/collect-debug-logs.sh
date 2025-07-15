#!/bin/bash
# Debug log collection script
echo "=== DEBUG LOG COLLECTION $(date) ==="
echo ""

echo "=== System Info ==="
echo "Hostname: $(hostname)"
echo "Uptime: $(uptime)"
echo "User: $(whoami)"
echo ""

echo "=== Systemd Service Status ==="
sudo systemctl status --no-pager bacalhau-startup.service
echo "---"
sudo systemctl status --no-pager setup-config.service  
echo "---"
sudo systemctl status --no-pager bacalhau.service
echo "---"
sudo systemctl status --no-pager sensor-generator.service
echo ""

echo "=== Docker Status ==="
docker version 2>&1 || echo "Docker not available"
echo "---"
docker ps -a
echo ""

echo "=== Main Startup Log (/opt/startup.log) ==="
if [ -f /opt/startup.log ]; then
    sudo tail -100 /opt/startup.log
else
    echo "File not found: /opt/startup.log"
fi
echo ""

echo "=== Recent Journal Entries ==="
sudo journalctl -n 50 --no-pager -u bacalhau-startup -u setup-config -u bacalhau -u sensor-generator
echo ""

echo "=== Docker Compose Logs ==="
if [ -f /opt/uploaded_files/scripts/docker-compose-bacalhau.yaml ]; then
    cd /opt/uploaded_files/scripts && docker compose -f docker-compose-bacalhau.yaml logs --tail=20 2>&1 || echo "No bacalhau compose logs"
fi
echo "---"
if [ -f /opt/uploaded_files/scripts/docker-compose-sensor.yaml ]; then
    cd /opt/uploaded_files/scripts && docker compose -f docker-compose-sensor.yaml logs --tail=20 2>&1 || echo "No sensor compose logs"
fi
echo ""

echo "=== Configuration Files Check ==="
ls -la /bacalhau_node/ 2>&1 || echo "/bacalhau_node/ not found"
echo "---"
ls -la /opt/sensor/config/ 2>&1 || echo "/opt/sensor/config/ not found"
echo ""

echo "=== Cloud-init Status ==="
cloud-init status --long 2>&1 || echo "cloud-init status not available"
echo ""

echo "=== END DEBUG LOG COLLECTION ==="