#!/bin/bash
# Main setup script for deployment
# This script runs after the deployment package is extracted

set -e  # Exit on error

echo "Starting amauo deployment setup..."

# First, deploy files from the extracted structure to their proper locations
echo "Deploying files to system locations..."

# Deploy usr files
if [ -d "usr" ]; then
    sudo cp -r usr/* /usr/ 2>/dev/null || true
fi

# Deploy etc files
if [ -d "etc" ]; then
    sudo cp -r etc/* /etc/ 2>/dev/null || true
fi

# Deploy opt files
if [ -d "opt" ]; then
    sudo cp -r opt/* /opt/ 2>/dev/null || true
fi

# Set proper permissions for scripts and services
sudo chmod +x /usr/local/bin/*.py 2>/dev/null || true
sudo chmod +x /usr/local/bin/*.sh 2>/dev/null || true
sudo chmod 644 /etc/systemd/system/*.service 2>/dev/null || true

echo "Files deployed successfully"

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sudo sh /tmp/get-docker.sh
    sudo usermod -aG docker ubuntu
    sudo systemctl enable docker
    sudo systemctl start docker
    echo "Docker installed and started"
else
    echo "Docker already installed"
fi

# Wait for Docker to be ready
echo "Waiting for Docker to be ready..."
sleep 5

# Reload systemd daemon to pick up new service files
sudo systemctl daemon-reload

# Enable services
echo "Enabling services..."
sudo systemctl enable bacalhau.service 2>/dev/null && echo "Enabled bacalhau.service" || echo "Could not enable bacalhau.service"
sudo systemctl enable sensor.service 2>/dev/null && echo "Enabled sensor.service" || echo "Could not enable sensor.service"

# Set up proper ownership and permissions for data directories
sudo mkdir -p /bacalhau_data /bacalhau_node /opt/bacalhau_node
sudo chown -R ubuntu:ubuntu /bacalhau_data /bacalhau_node /opt/uploaded_files 2>/dev/null || true
sudo chmod 755 /bacalhau_data /bacalhau_node 2>/dev/null || true

# Generate node identity if the script exists
if [ -x /usr/local/bin/generate_node_identity.py ]; then
    echo "Generating node identity..."
    sudo -u ubuntu /usr/local/bin/generate_node_identity.py
fi

# Start services (Docker should be ready now)
echo "Starting services..."
sudo systemctl start bacalhau.service 2>/dev/null && echo "Started bacalhau.service" || echo "Could not start bacalhau.service"
sudo systemctl start sensor.service 2>/dev/null && echo "Started sensor.service" || echo "Could not start sensor.service"

echo "✅ Amauo deployment setup complete!"