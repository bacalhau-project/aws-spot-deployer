#!/bin/bash
# Quick fix script for common deployment issues

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <instance-ip>"
    exit 1
fi

INSTANCE_IP=$1
SSH_KEY=${SSH_KEY:-~/.ssh/id_rsa}

echo "=== Applying deployment fixes to $INSTANCE_IP ==="

# Create remote fix script
cat << 'EOF' > /tmp/remote_fix.sh
#!/bin/bash
echo "=== Starting deployment fix ==="

# 1. Ensure startup log exists
sudo touch /opt/startup.log
sudo chown ubuntu:ubuntu /opt/startup.log

# 2. Create all required directories
echo "Creating directories..."
sudo mkdir -p /bacalhau_node /bacalhau_data 
sudo mkdir -p /opt/sensor/{config,data,logs,exports}
sudo mkdir -p /opt/uploaded_files/{scripts,config}
sudo chown -R ubuntu:ubuntu /bacalhau_node /bacalhau_data /opt/sensor /opt/uploaded_files

# 3. Fix script permissions
echo "Fixing script permissions..."
if [ -d /opt/uploaded_files/scripts ]; then
    sudo chmod +x /opt/uploaded_files/scripts/*.sh 2>/dev/null || true
    sudo chmod +x /opt/uploaded_files/scripts/*.py 2>/dev/null || true
fi

# 4. Copy systemd service files
echo "Copying systemd service files..."
for service in bacalhau-startup setup-config bacalhau sensor-generator; do
    if [ -f /opt/uploaded_files/scripts/${service}.service ]; then
        sudo cp /opt/uploaded_files/scripts/${service}.service /etc/systemd/system/
        echo "  Copied ${service}.service"
    fi
done

# 5. Reload systemd
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# 6. Start services in correct order
echo "Starting services..."
sudo systemctl start bacalhau-startup.service
sleep 2
sudo systemctl start setup-config.service
sleep 2
sudo systemctl start bacalhau.service
sudo systemctl start sensor-generator.service

# 7. Show status
echo ""
echo "=== Service Status ==="
for service in bacalhau-startup setup-config bacalhau sensor-generator; do
    echo "--- $service ---"
    sudo systemctl is-active $service.service || echo "Not active"
done

echo ""
echo "=== Docker Status ==="
docker ps -a

echo ""
echo "=== Fix Complete ==="
echo "Check /opt/startup.log for details"
EOF

# Make it executable
chmod +x /tmp/remote_fix.sh

# Copy and run on remote
echo "Copying fix script to instance..."
scp -i $SSH_KEY -o StrictHostKeyChecking=no /tmp/remote_fix.sh ubuntu@$INSTANCE_IP:/tmp/

echo "Running fix script..."
ssh -i $SSH_KEY -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP "bash /tmp/remote_fix.sh"

# Cleanup
rm /tmp/remote_fix.sh

echo ""
echo "Fix attempted. Run ./debug_deployment.sh $INSTANCE_IP to check status"