#!/bin/bash
# Debug script for systemd services

echo "=== Service Debug Information ==="
echo

echo "1. Checking service dependencies:"
echo "--------------------------------"
systemctl list-dependencies bacalhau-startup.service
echo
systemctl list-dependencies setup-config.service
echo
systemctl list-dependencies bacalhau.service
echo
systemctl list-dependencies sensor-generator.service
echo

echo "2. Checking if start-bacalhau-stack.service ran:"
echo "--------------------------------"
systemctl status start-bacalhau-stack.service --no-pager
echo

echo "3. Checking setup-config.service journal:"
echo "--------------------------------"
sudo journalctl -u setup-config.service --no-pager -n 50
echo

echo "4. Checking bacalhau.service journal:"
echo "--------------------------------"
sudo journalctl -u bacalhau.service --no-pager -n 50
echo

echo "5. Checking if directories were created:"
echo "--------------------------------"
ls -la /bacalhau_node/ 2>/dev/null || echo "/bacalhau_node/ not found"
ls -la /bacalhau_data/ 2>/dev/null || echo "/bacalhau_data/ not found"
ls -la /opt/sensor/ 2>/dev/null || echo "/opt/sensor/ not found"
echo

echo "6. Checking if config files exist:"
echo "--------------------------------"
ls -la /opt/uploaded_files/config/ 2>/dev/null || echo "Config directory not found"
echo

echo "7. Checking startup log:"
echo "--------------------------------"
cat /opt/startup.log
echo

echo "8. Checking service conditions:"
echo "--------------------------------"
# Check if the condition file exists for bacalhau-startup
ls -la /opt/uploaded_files/scripts/simple-startup.py
echo

echo "9. Manually starting setup-config:"
echo "--------------------------------"
echo "Attempting to start setup-config.service..."
sudo systemctl start setup-config.service
sleep 2
systemctl status setup-config.service --no-pager
echo

echo "10. Check for any failed services:"
echo "--------------------------------"
systemctl list-units --failed