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

# Set proper permissions for scripts and services (be very specific)
find /usr/local/bin -name "*.py" -exec sudo chmod 755 {} \; 2>/dev/null || true
find /usr/local/bin -name "*.sh" -exec sudo chmod 755 {} \; 2>/dev/null || true
find /etc/systemd/system -name "*.service" -exec sudo chmod 644 {} \; 2>/dev/null || true

echo "Files deployed successfully"

# Install uv (required for Python scripts) as ubuntu user
if ! sudo -u ubuntu bash -c 'command -v uv' &> /dev/null; then
    echo "Installing uv..."
    sudo -u ubuntu bash -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'
    # Create system-wide symlink for uv so shebangs work
    sudo ln -sf /home/ubuntu/.local/bin/uv /usr/local/bin/uv
    sudo ln -sf /home/ubuntu/.local/bin/uvx /usr/local/bin/uvx
    echo "uv installed successfully and made available system-wide"
else
    echo "uv already installed"
fi

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."

    # Install GPG tools first to fix verification issues
    sudo apt-get update -qq || true
    sudo apt-get install -y gnupg lsb-release ca-certificates curl || true

    # Try the official Docker installation script
    if curl -fsSL https://get.docker.com -o /tmp/get-docker.sh 2>/dev/null; then
        sudo sh /tmp/get-docker.sh 2>/dev/null || {
            echo "Docker script failed, trying alternative installation..."
            # Fallback: install from Ubuntu repositories
            sudo apt-get update -qq || true
            sudo apt-get install -y docker.io docker-compose || true
        }
    else
        echo "Could not download Docker script, using package manager..."
        sudo apt-get update -qq || true
        sudo apt-get install -y docker.io docker-compose || true
    fi

    # Configure Docker
    sudo usermod -aG docker ubuntu || true
    sudo systemctl enable docker || true
    sudo systemctl start docker || true

    # Clean up
    rm -f /tmp/get-docker.sh

    # Verify installation
    if command -v docker &> /dev/null; then
        echo "Docker installed and started successfully"
    else
        echo "Warning: Docker installation may have failed"
    fi
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
sudo mkdir -p /opt/sensor/config /opt/sensor/logs /opt/sensor/data /opt/sensor/exports
sudo mkdir -p /opt/uploaded_files/scripts
sudo chown -R ubuntu:ubuntu /bacalhau_data /bacalhau_node /opt/uploaded_files /opt/sensor 2>/dev/null || true
sudo chmod 755 /bacalhau_data /bacalhau_node /opt/sensor 2>/dev/null || true

# Copy docker-compose files to scripts directory for services
if [ -f /opt/uploaded_files/docker-compose-bacalhau.yaml ]; then
    sudo -u ubuntu cp /opt/uploaded_files/docker-compose-bacalhau.yaml /opt/uploaded_files/scripts/
fi


# Generate Bacalhau configuration from template - STRICT MODE
echo "Generating Bacalhau configuration from template..."

# STRICT: Check for required files
if [ ! -f /opt/uploaded_files/bacalhau-config-template.yaml ]; then
    echo "ERROR: Bacalhau config template not found at /opt/uploaded_files/bacalhau-config-template.yaml"
    echo "ERROR: Required template file is missing from deployment"
    exit 1
fi

if [ ! -f /opt/uploaded_files/orchestrator_endpoint ]; then
    echo "ERROR: Orchestrator endpoint file not found at /opt/uploaded_files/orchestrator_endpoint"
    echo "ERROR: Required credential file is missing from deployment"
    exit 1
fi

if [ ! -f /opt/uploaded_files/orchestrator_token ]; then
    echo "ERROR: Orchestrator token file not found at /opt/uploaded_files/orchestrator_token"
    echo "ERROR: Required credential file is missing from deployment"
    exit 1
fi

# STRICT: Read credentials and validate
ENDPOINT=$(cat /opt/uploaded_files/orchestrator_endpoint | tr -d '[:space:]')
TOKEN=$(cat /opt/uploaded_files/orchestrator_token | tr -d '[:space:]')

if [ -z "$ENDPOINT" ]; then
    echo "ERROR: Orchestrator endpoint is empty"
    echo "ERROR: Invalid or empty orchestrator endpoint file"
    exit 1
fi

if [ -z "$TOKEN" ]; then
    echo "ERROR: Orchestrator token is empty"
    echo "ERROR: Invalid or empty orchestrator token file"
    exit 1
fi

echo "SUCCESS: Using orchestrator endpoint: $ENDPOINT"
echo "SUCCESS: Using orchestrator token: ${TOKEN:0:15}..."

# STRICT: Render template with validation
echo "SUCCESS: Rendering Bacalhau config from template..."
if ! sed -e "s|{{ORCHESTRATOR_ENDPOINT}}|$ENDPOINT|g" \
         -e "s|{{ORCHESTRATOR_TOKEN}}|$TOKEN|g" \
         /opt/uploaded_files/bacalhau-config-template.yaml | sudo -u ubuntu tee /bacalhau_node/config.yaml > /dev/null; then
    echo "ERROR: Failed to render Bacalhau config template"
    echo "ERROR: Template rendering failed - deployment aborted"
    exit 1
fi

echo "SUCCESS: Bacalhau configuration generated from template"


# Generate node identity if the script exists
if [ -x /usr/local/bin/generate_node_identity.py ]; then
    echo "Generating node identity..."
    # Run the script with proper output path (uv should now be available system-wide)
    sudo -u ubuntu /usr/local/bin/generate_node_identity.py -o /opt/sensor/config/node_identity.json
fi

# Start services (Docker should be ready now)
echo "Starting services..."
sudo systemctl start bacalhau.service 2>/dev/null && echo "Started bacalhau.service" || echo "Could not start bacalhau.service"
sudo systemctl start sensor.service 2>/dev/null && echo "Started sensor.service" || echo "Could not start sensor.service"

echo "✅ Amauo deployment setup complete!"
