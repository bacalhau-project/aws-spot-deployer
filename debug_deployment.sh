#!/bin/bash
# debug_deployment.sh - Comprehensive deployment debugging script
# Usage: ./debug_deployment.sh <instance-ip>

IP=$1
KEY=${2:-~/.ssh/id_rsa}  # Optional SSH key path

if [ -z "$IP" ]; then
    echo "Usage: $0 <instance-ip> [ssh-key-path]"
    exit 1
fi

echo "=== Debugging Deployment on $IP ==="
echo "Using SSH key: $KEY"
echo

# Function to run SSH commands
ssh_cmd() {
    ssh -i "$KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ubuntu@$IP "$1" 2>/dev/null
}

echo "=== 1. CLOUD-INIT STATUS ==="
echo "Cloud-init status:"
ssh_cmd "sudo cloud-init status --wait"
echo
echo "Cloud-init completion marker:"
ssh_cmd "ls -la /tmp/cloud-init-complete"
echo

echo "=== 2. WATCHER SCRIPT ==="
echo "Watcher script location:"
ssh_cmd "ls -la /usr/local/bin/watch-for-deployment.sh"
echo
echo "Watcher process:"
ssh_cmd "ps aux | grep -E 'watch-for-deployment|deploy_services'"
echo
echo "Watcher log:"
ssh_cmd "cat /tmp/watcher.log | tail -20"
echo

echo "=== 3. PACKAGE INSTALLATION ==="
echo "Docker:"
ssh_cmd "docker --version && systemctl is-active docker"
echo
echo "UV installation:"
ssh_cmd "which uv && uv --version"
ssh_cmd "ls -la /usr/bin/uv /usr/local/bin/uv"
echo

echo "=== 4. FILE UPLOAD STATUS ==="
echo "Upload marker:"
ssh_cmd "ls -la /tmp/uploaded_files_ready"
echo
echo "Temporary upload directory:"
ssh_cmd "ls -la /tmp/uploaded_files/ 2>&1 || echo 'Directory not found (expected if deployment ran)'"
echo
echo "Final upload directory:"
ssh_cmd "ls -la /opt/uploaded_files/"
ssh_cmd "ls -la /opt/uploaded_files/scripts/"
ssh_cmd "ls -la /opt/uploaded_files/config/"
echo

echo "=== 5. DEPLOYMENT LOGS ==="
echo "Startup log:"
ssh_cmd "cat /opt/startup.log"
echo
echo "Deployment log (home):"
ssh_cmd "cat /home/ubuntu/deployment.log | tail -50"
echo
echo "Deployment log (opt):"
ssh_cmd "cat /opt/deployment.log | tail -50"
echo

echo "=== 6. DIRECTORY STRUCTURE ==="
echo "Required directories:"
ssh_cmd "ls -la /bacalhau_node/ /bacalhau_data/ /opt/sensor/"
echo
echo "Config files:"
ssh_cmd "ls -la /bacalhau_node/config.yaml"
ssh_cmd "ls -la /opt/sensor/config/node_identity.json"
echo

echo "=== 7. SYSTEMD SERVICES ==="
echo "Service files:"
ssh_cmd "ls -la /etc/systemd/system/*.service | grep -E 'bacalhau|sensor'"
echo
echo "Service status:"
ssh_cmd "systemctl status bacalhau.service --no-pager"
ssh_cmd "systemctl status sensor-generator.service --no-pager"
echo

echo "=== 8. DOCKER CONTAINERS ==="
ssh_cmd "docker ps -a"
echo

echo "=== 9. DEPLOYMENT COMPLETION ==="
echo "Completion marker:"
ssh_cmd "cat /opt/deployment_complete"
echo
echo "System uptime (to check if reboot happened):"
ssh_cmd "uptime"
echo

echo "=== 10. RECENT SYSTEM LOGS ==="
ssh_cmd "sudo journalctl -n 100 --no-pager | grep -E 'deployment|bacalhau|docker|error|fail' | tail -30"
echo

echo "=== 11. CLOUD-INIT DETAILED LOG ==="
echo "Last 50 lines of cloud-init output:"
ssh_cmd "sudo tail -50 /var/log/cloud-init-output.log"
echo

echo "=== QUICK DIAGNOSIS ==="
echo -n "Cloud-init: "
ssh_cmd "sudo cloud-init status --wait | grep -q 'done' && echo 'COMPLETE' || echo 'FAILED/RUNNING'"

echo -n "Watcher running: "
ssh_cmd "pgrep -f watch-for-deployment > /dev/null && echo 'YES' || echo 'NO'"

echo -n "Files uploaded: "
ssh_cmd "[ -f /tmp/uploaded_files_ready ] && echo 'YES' || echo 'NO'"

echo -n "Deployment ran: "
ssh_cmd "[ -f /opt/deployment_complete ] && echo 'YES' || echo 'NO'"

echo -n "Bacalhau running: "
ssh_cmd "docker ps | grep -q bacalhau && echo 'YES' || echo 'NO'"

echo
echo "=== DEBUG COMPLETE ==="