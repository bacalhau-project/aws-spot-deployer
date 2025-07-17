#!/bin/bash
# Debug script for spot instance deployment issues

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <instance-ip>"
    exit 1
fi

INSTANCE_IP=$1
SSH_KEY=${SSH_KEY:-~/.ssh/id_rsa}

echo "=== Debugging deployment on $INSTANCE_IP ==="
echo "Using SSH key: $SSH_KEY"
echo ""

# Create remote debug script
cat << 'EOF' > /tmp/remote_debug.sh
#!/bin/bash
echo "=== Instance Debug Report ==="
echo "Date: $(date)"
echo "Hostname: $(hostname)"
echo "Instance ID: $(curl -s http://169.254.169.254/latest/meta-data/instance-id)"
echo ""

echo "=== Cloud-Init Status ==="
cloud-init status --long 2>/dev/null || echo "cloud-init command not found"
echo ""

echo "=== Uploaded Files Check ==="
echo "Contents of /opt/uploaded_files:"
find /opt/uploaded_files -type f -ls 2>/dev/null | head -20
echo ""

echo "=== Service Status ==="
for service in bacalhau-startup setup-config bacalhau sensor-generator; do
    echo "--- $service.service ---"
    sudo systemctl status $service.service --no-pager -n 3
    echo ""
done

echo "=== Startup Log (last 50 lines) ==="
sudo tail -n 50 /opt/startup.log 2>/dev/null || echo "No startup.log found"
echo ""

echo "=== Directory Structure ==="
for dir in /bacalhau_node /bacalhau_data /opt/sensor; do
    echo "Checking $dir:"
    ls -la $dir 2>/dev/null || echo "  Directory not found"
done
echo ""

echo "=== Docker Status ==="
docker ps -a 2>/dev/null || echo "Docker not running or not installed"
echo ""

echo "=== Bacalhau Config ==="
if [ -f /bacalhau_node/config.yaml ]; then
    echo "Config exists. Orchestrator settings:"
    grep -A5 "Orchestrators\|Token" /bacalhau_node/config.yaml 2>/dev/null
else
    echo "Bacalhau config not found"
fi
echo ""

echo "=== Recent Service Logs ==="
sudo journalctl -u bacalhau-startup -u setup-config -u bacalhau --since "5 minutes ago" --no-pager | tail -30
EOF

# Make it executable
chmod +x /tmp/remote_debug.sh

# Copy and run on remote
echo "Copying debug script to instance..."
scp -i $SSH_KEY -o StrictHostKeyChecking=no /tmp/remote_debug.sh ubuntu@$INSTANCE_IP:/tmp/
echo ""
echo "Running debug script..."
ssh -i $SSH_KEY -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP "bash /tmp/remote_debug.sh"

# Cleanup
rm /tmp/remote_debug.sh