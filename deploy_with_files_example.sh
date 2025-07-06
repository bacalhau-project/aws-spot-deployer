#!/bin/bash
# Example deployment script that uses uploaded files
# This script demonstrates how to access files uploaded via the files directory

echo "=== Deployment Script with Files Support ==="
echo "Hostname: $(hostname)"
echo "Current user: $(whoami)"
echo "Date/Time: $(date)"

# Check if files directory is available
if [ -n "$DEPLOY_FILES_DIR" ] && [ -d "$DEPLOY_FILES_DIR" ]; then
    echo -e "\n=== Files Directory Available ==="
    echo "Files directory: $DEPLOY_FILES_DIR"
    echo "Contents:"
    ls -la "$DEPLOY_FILES_DIR"
    
    # Process configuration file
    CONFIG_FILE="$DEPLOY_FILES_DIR/app.config"
    if [ -f "$CONFIG_FILE" ]; then
        echo -e "\n=== Processing Configuration File ==="
        echo "Found app.config, deploying to /etc/myapp/"
        sudo mkdir -p /etc/myapp
        sudo cp "$CONFIG_FILE" /etc/myapp/
        echo "Configuration deployed successfully"
        
        # Show database configuration
        if grep -q "\[database\]" "$CONFIG_FILE"; then
            echo "Database configuration found:"
            grep -A 5 "\[database\]" "$CONFIG_FILE"
        fi
    fi
    
    # Process credentials file
    CREDENTIALS_FILE="$DEPLOY_FILES_DIR/credentials.json"
    if [ -f "$CREDENTIALS_FILE" ]; then
        echo -e "\n=== Processing Credentials File ==="
        echo "Found credentials.json, setting up secure access..."
        sudo mkdir -p /etc/myapp
        sudo cp "$CREDENTIALS_FILE" /etc/myapp/credentials.json
        sudo chmod 600 /etc/myapp/credentials.json
        sudo chown root:root /etc/myapp/credentials.json
        echo "Credentials deployed securely"
    fi
    
    # Process data file
    DATA_FILE="$DEPLOY_FILES_DIR/deployment_data.csv"
    if [ -f "$DATA_FILE" ]; then
        echo -e "\n=== Processing Deployment Data ==="
        echo "Found deployment_data.csv:"
        echo "Services to deploy:"
        head -6 "$DATA_FILE" | column -t -s,
        
        # Count services
        SERVICE_COUNT=$(tail -n +2 "$DATA_FILE" | wc -l)
        echo "Total services: $SERVICE_COUNT"
    fi
    
else
    echo -e "\n=== No Files Directory ==="
    echo "DEPLOY_FILES_DIR not set or directory not found"
    echo "Running script without additional files"
fi

# Perform deployment tasks
echo -e "\n=== Deployment Tasks ==="
echo "1. Updating system packages..."
sudo apt update -qq

echo "2. Installing required packages..."
sudo apt install -y curl wget jq

echo "3. Setting up application directory..."
sudo mkdir -p /opt/myapp
sudo chown $USER:$USER /opt/myapp

echo "4. Creating systemd service file..."
sudo tee /etc/systemd/system/myapp.service > /dev/null << EOF
[Unit]
Description=My Application
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/myapp
ExecStart=/opt/myapp/start.sh
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo "5. Enabling service..."
sudo systemctl enable myapp.service

# Test network connectivity
echo -e "\n=== Network Connectivity Tests ==="
echo "External IP: $(curl -s https://ipinfo.io/ip || echo 'Unable to determine')"
echo "DNS test: $(nslookup google.com > /dev/null && echo 'DNS working' || echo 'DNS issues')"

# System information
echo -e "\n=== System Information ==="
echo "OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
echo "Kernel: $(uname -r)"
echo "Architecture: $(uname -m)"
echo "Memory: $(free -h | grep Mem | awk '{print $2}')"
echo "Disk space: $(df -h / | tail -1 | awk '{print $4}' | sed 's/G/ GB/')"

echo -e "\n=== Deployment Completed Successfully ==="
exit 0