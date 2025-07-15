#!/bin/bash
# Debug script to check cloud-init status and logs

echo "=== Cloud-Init Debug Information ==="
echo

echo "1. Cloud-init status:"
cloud-init status --wait --long
echo

echo "2. Cloud-init version:"
cloud-init --version
echo

echo "3. Checking for status files:"
echo "- /tmp/cloud-init-status:"
ls -la /tmp/cloud-init-status 2>/dev/null || echo "  File not found"
echo "- /var/log/startup-progress.log:"
ls -la /var/log/startup-progress.log 2>/dev/null || echo "  File not found"
echo "- /opt/startup.log:"
ls -la /opt/startup.log 2>/dev/null || echo "  File not found"
echo

echo "4. Checking directories created by cloud-init:"
echo "- /opt/uploaded_files:"
ls -la /opt/uploaded_files/ 2>/dev/null || echo "  Directory not found"
echo "- /tmp/exs:"
ls -la /tmp/exs/ 2>/dev/null || echo "  Directory not found"
echo

echo "5. Last 50 lines of cloud-init output log:"
echo "----------------------------------------"
sudo tail -50 /var/log/cloud-init-output.log 2>/dev/null || echo "Log file not found"
echo

echo "6. Checking for cloud-init errors:"
echo "----------------------------------------"
sudo grep -i error /var/log/cloud-init.log | tail -20 2>/dev/null || echo "No errors found or log not accessible"
echo

echo "7. Checking user-data:"
echo "----------------------------------------"
sudo cat /var/lib/cloud/instance/user-data.txt | head -20 2>/dev/null || echo "User data not found"
echo "... (truncated)"
echo

echo "8. Checking if our runcmd executed:"
echo "----------------------------------------"
sudo journalctl -u cloud-init --no-pager | grep -E "(Package updates starting|Upload directories created|Installing Docker)" | tail -10
echo

echo "9. Checking systemd services:"
echo "----------------------------------------"
systemctl list-units --all | grep -E "(bacalhau|sensor|setup)"
echo

echo "10. Docker status:"
docker --version 2>/dev/null || echo "Docker not installed"
sudo systemctl status docker --no-pager | head -10
echo

echo "=== End of Debug Information ==="