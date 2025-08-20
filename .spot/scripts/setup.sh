#!/bin/bash
# Post-Setup Script - Main deployment logic
# This runs after cloud-init has prepared the system and files are uploaded

set -e  # Exit on error

echo "Starting deployment setup at $(date)"

# ==============================================================================
# TARBALL EXTRACTION (if configured in deployment.yaml)
# ==============================================================================
if [ -d /opt/deployer ]; then
    echo "Found /opt/deployer directory from tarball"
    ls -la /opt/deployer/

    # Run setup script from tarball if it exists
    if [ -f /opt/deployer/node/setup.sh ]; then
        echo "Running setup script from tarball..."
        chmod +x /opt/deployer/node/setup.sh
        /opt/deployer/node/setup.sh
    fi
fi

# ==============================================================================
# SERVICE INSTALLATION (from tarball or uploaded files)
# ==============================================================================
# Install services from tarball
if [ -d /opt/deployer/node/services ]; then
    echo "Installing services from tarball..."
    for service in /opt/deployer/node/services/*.service; do
        if [ -f "$service" ]; then
            service_name=$(basename "$service")
            echo "Installing service: $service_name"
            sudo cp "$service" /etc/systemd/system/
            sudo systemctl daemon-reload
            sudo systemctl enable "$service_name"
            sudo systemctl start "$service_name"
        fi
    done
fi

# Install services from uploaded files
if [ -d /opt/uploaded_files/services ]; then
    echo "Installing services from uploaded files..."
    for service in /opt/uploaded_files/services/*.service; do
        if [ -f "$service" ]; then
            service_name=$(basename "$service")
            echo "Installing service: $service_name"
            sudo cp "$service" /etc/systemd/system/
            sudo systemctl daemon-reload
            sudo systemctl enable "$service_name"
            sudo systemctl start "$service_name"
        fi
    done
fi

# ==============================================================================
# USER CUSTOM SETUP
# ==============================================================================
# Add your application-specific setup commands below.
# This section is where you customize the deployment for your specific needs.
#
# Examples:
# - Clone git repositories
# - Install application dependencies (npm install, pip install, etc.)
# - Configure environment variables
# - Initialize databases
# - Build your application
# - Start application services

# Example: Install Python requirements
# if [ -f /opt/uploaded_files/requirements.txt ]; then
#     echo "Installing Python requirements..."
#     pip3 install -r /opt/uploaded_files/requirements.txt
# fi

# Example: Clone and setup a Node.js application
# cd /opt/deployer/node
# git clone https://github.com/yourorg/yourapp.git
# cd yourapp
# npm install --production
# npm run build

# YOUR CUSTOM SETUP GOES HERE:




# ==============================================================================
# COMPLETION
# ==============================================================================
echo "Deployment setup completed at $(date)"

# Create completion marker
touch /opt/deployer/deployment_complete

# Show final status
echo "=== Deployment Status ==="
systemctl list-units --state=running --no-pager | grep -E "(docker|deployer)" || true
echo "========================"
