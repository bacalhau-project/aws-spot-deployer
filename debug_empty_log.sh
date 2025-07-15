#!/bin/bash
# Debug why startup.log is empty

echo "=== Checking why /opt/startup.log is empty ==="
echo ""

echo "=== File permissions ==="
ls -la /opt/startup.log

echo ""
echo "=== Cloud-init status ==="
cloud-init status --long

echo ""
echo "=== Check if services are enabled ==="
systemctl list-unit-files | grep -E "(bacalhau-startup|setup-config|bacalhau|sensor-generator).service"

echo ""
echo "=== Service status ==="
echo "--- bacalhau-startup.service ---"
sudo systemctl status bacalhau-startup.service --no-pager
echo ""
echo "--- setup-config.service ---"
sudo systemctl status setup-config.service --no-pager
echo ""
echo "--- bacalhau.service ---"
sudo systemctl status bacalhau.service --no-pager
echo ""
echo "--- sensor-generator.service ---"
sudo systemctl status sensor-generator.service --no-pager

echo ""
echo "=== Check if service files exist ==="
ls -la /etc/systemd/system/ | grep -E "(bacalhau-startup|setup-config|bacalhau|sensor-generator).service"

echo ""
echo "=== Journal logs for our services ==="
sudo journalctl -u bacalhau-startup -u setup-config -u bacalhau -u sensor-generator --no-pager -n 50

echo ""
echo "=== Check if scripts exist ==="
ls -la /opt/uploaded_files/scripts/

echo ""
echo "=== Cloud-init output log (last 50 lines) ==="
sudo tail -50 /var/log/cloud-init-output.log

echo ""
echo "=== Check for any startup attempts in syslog ==="
sudo grep -i "startup\|bacalhau\|sensor" /var/log/syslog | tail -20