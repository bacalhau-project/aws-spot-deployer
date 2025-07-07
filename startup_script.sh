#!/bin/bash
# Default startup script for AWS Spot Deployer
# This script is automatically uploaded and executed after instance creation

echo "=== AWS Spot Instance Startup Script ==="
echo "Hostname: $(hostname)"
echo "Date/Time: $(date)"
echo "User: $(whoami)"

# Check if files were uploaded
if [ -n "$DEPLOY_FILES_DIR" ] && [ -d "$DEPLOY_FILES_DIR" ]; then
    echo -e "\n=== Processing Uploaded Files ==="
    echo "Files directory: $DEPLOY_FILES_DIR"
    echo "Uploaded files:"
    ls -la "$DEPLOY_FILES_DIR"
    
    # Example: Process configuration files
    if [ -f "$DEPLOY_FILES_DIR/config.env" ]; then
        echo "Loading configuration from config.env"
        source "$DEPLOY_FILES_DIR/config.env"
    fi
    
    # Example: Process credentials file
    if [ -f "$DEPLOY_FILES_DIR/credentials.json" ]; then
        echo "Processing credentials file"
        # Copy to secure location
        sudo mkdir -p /etc/app
        sudo cp "$DEPLOY_FILES_DIR/credentials.json" /etc/app/
        sudo chmod 600 /etc/app/credentials.json
        echo "Credentials installed securely"
    fi
else
    echo -e "\n=== No Files Uploaded ==="
    echo "DEPLOY_FILES_DIR not set or directory not found"
fi

# System updates and basic setup
echo -e "\n=== System Setup ==="
echo "Updating package list..."
sudo apt update -qq

echo "Installing essential packages..."
sudo apt install -y curl wget jq htop

# Docker setup (if not already done by user-data)
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    sudo apt install -y docker.io
    sudo systemctl enable docker
    sudo systemctl start docker
    sudo usermod -aG docker ubuntu
fi

# Check Docker status
echo "Docker status: $(systemctl is-active docker)"
echo "Docker version: $(docker --version)"

# Example application setup
echo -e "\n=== Application Setup ==="
echo "Creating application directory..."
sudo mkdir -p /opt/myapp
sudo chown ubuntu:ubuntu /opt/myapp

# Example: Download and setup application
# wget -O /opt/myapp/app.tar.gz https://releases.example.com/app.tar.gz
# tar -xzf /opt/myapp/app.tar.gz -C /opt/myapp

# Network and connectivity tests
echo -e "\n=== Network Connectivity ==="
echo "External IP: $(curl -s https://ipinfo.io/ip || echo 'Unable to determine')"
echo "DNS test: $(nslookup google.com > /dev/null && echo 'DNS working' || echo 'DNS issues')"

# System information
echo -e "\n=== System Information ==="
echo "OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
echo "Kernel: $(uname -r)"
echo "Architecture: $(uname -m)"
echo "CPU cores: $(nproc)"
echo "Memory: $(free -h | grep Mem | awk '{print $2}')"
echo "Disk space: $(df -h / | tail -1 | awk '{print $4}')"

# Success message
echo -e "\n=== Startup Script Completed Successfully ==="
echo "Instance is ready for use!"

exit 0