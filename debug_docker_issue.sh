#!/bin/bash
# Docker debugging script
# Usage: ./debug_docker_issue.sh <instance-ip>

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
echo "Docker Installation Debug Report for $INSTANCE_IP"
echo "==================================================="
echo "Date: $(date)"
echo ""

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$USERNAME@$INSTANCE_IP" 'bash -s' << 'ENDSSH'
echo "=== SYSTEM INFO ==="
echo "Hostname: $(hostname)"
echo "Uptime: $(uptime)"
echo "Kernel: $(uname -r)"
echo ""

echo "=== DOCKER INSTALLATION STATUS ==="
echo "--- Docker Package Status ---"
dpkg -l | grep -E "docker|containerd" || echo "No Docker packages found"
echo ""

echo "--- Docker Service Status ---"
sudo systemctl status docker --no-pager || echo "Docker service not found"
echo ""

echo "--- Docker Socket Check ---"
ls -la /var/run/docker.sock 2>/dev/null || echo "Docker socket not found"
echo ""

echo "--- Docker Version ---"
docker --version 2>&1 || echo "Docker command not available"
echo ""

echo "--- Docker Compose Version ---"
docker compose version 2>&1 || echo "Docker Compose not available"
echo ""

echo "=== APT STATUS CHECK ==="
echo "--- Check for incomplete installations ---"
sudo dpkg --audit
echo ""

echo "--- Check APT locks ---"
sudo lsof /var/lib/dpkg/lock-frontend 2>/dev/null || echo "No lock on dpkg frontend"
sudo lsof /var/lib/apt/lists/lock 2>/dev/null || echo "No lock on apt lists"
echo ""

echo "=== CLOUD-INIT LOGS (Docker related) ==="
echo "--- Last 50 lines mentioning docker ---"
sudo grep -i docker /var/log/cloud-init-output.log | tail -50 || echo "No docker entries found"
echo ""

echo "=== SYSTEM LOGS (Docker related) ==="
echo "--- Journal entries for docker ---"
sudo journalctl -u docker --no-pager -n 30 || echo "No docker journal entries"
echo ""

echo "=== STARTUP SERVICE LOGS ==="
echo "--- Bacalhau startup service ---"
sudo systemctl status bacalhau-startup.service --no-pager || echo "Service not found"
echo ""
echo "--- Journal for bacalhau-startup ---"
sudo journalctl -u bacalhau-startup.service --no-pager -n 20 || echo "No logs"
echo ""

echo "=== STARTUP LOG FILE ==="
if [ -f /opt/startup.log ]; then
    echo "--- Last 30 lines of /opt/startup.log ---"
    sudo tail -30 /opt/startup.log
else
    echo "/opt/startup.log not found"
fi
echo ""

echo "=== FIX SUGGESTIONS ==="
echo "If Docker installation is incomplete, try:"
echo "1. sudo dpkg --configure -a"
echo "2. sudo apt-get update"
echo "3. sudo apt-get install -f"
echo "4. sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin"
echo "5. sudo systemctl start docker"
echo "6. sudo systemctl enable docker"
echo ""

echo "=== ATTEMPTING AUTO-FIX ==="
echo "Trying to fix Docker installation..."

# Fix incomplete installations
sudo dpkg --configure -a 2>&1 || echo "dpkg configure failed"

# Update package lists
sudo apt-get update 2>&1 || echo "apt update failed"

# Fix broken dependencies
sudo apt-get install -f -y 2>&1 || echo "apt install -f failed"

# Try to complete Docker installation
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin 2>&1 || echo "Docker installation failed"

# Start Docker service
sudo systemctl start docker 2>&1 || echo "Failed to start docker"
sudo systemctl enable docker 2>&1 || echo "Failed to enable docker"

# Add user to docker group
sudo usermod -aG docker ubuntu 2>&1 || echo "Failed to add user to docker group"

echo ""
echo "=== POST-FIX STATUS ==="
echo "Docker service status:"
sudo systemctl is-active docker || echo "Docker not active"
echo ""
echo "Docker version:"
docker --version 2>&1 || echo "Docker still not working"
echo ""
echo "Docker test:"
sudo docker run hello-world 2>&1 || echo "Docker test failed"
echo ""

echo "==================================================="
echo "Debug report complete"
echo "==================================================="
ENDSSH