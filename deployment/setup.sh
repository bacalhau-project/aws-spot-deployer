#!/bin/bash
# Setup script for Bacalhau compute node and sensor simulator

set -e

echo "[$(date)] Setting up Bacalhau compute node and sensor simulator..."

# Files are already in their proper locations from the tarball extraction
# The tarball mirrors the filesystem structure, so files are at:
# /opt/deployment/etc/bacalhau/config.yaml -> /etc/bacalhau/config.yaml
# /opt/deployment/opt/bacalhau/docker-compose.yml -> /opt/bacalhau/docker-compose.yml
# /opt/deployment/opt/sensor/* -> /opt/sensor/*
# /opt/deployment/etc/systemd/system/bacalhau.service -> /etc/systemd/system/bacalhau.service

# Create actual directories on the system
mkdir -p /etc/bacalhau
mkdir -p /opt/bacalhau
mkdir -p /var/log/bacalhau
mkdir -p /opt/sensor/config
mkdir -p /opt/sensor/data
mkdir -p /root/.aws

# Copy files from deployment structure to their final locations
if [ -f /opt/deployment/etc/bacalhau/config.yaml ]; then
    cp /opt/deployment/etc/bacalhau/config.yaml /etc/bacalhau/config.yaml
    echo "[$(date)] Copied Bacalhau config to /etc/bacalhau/"
fi

if [ -f /opt/deployment/opt/bacalhau/docker-compose.yml ]; then
    cp /opt/deployment/opt/bacalhau/docker-compose.yml /opt/bacalhau/docker-compose.yml
    echo "[$(date)] Copied docker-compose.yml to /opt/bacalhau/"
fi

if [ -f /opt/deployment/etc/systemd/system/bacalhau.service ]; then
    cp /opt/deployment/etc/systemd/system/bacalhau.service /etc/systemd/system/bacalhau.service
    echo "[$(date)] Copied systemd service file"
    systemctl daemon-reload
fi

# Copy sensor files
if [ -d /opt/deployment/opt/sensor ]; then
    cp -r /opt/deployment/opt/sensor/* /opt/sensor/
    echo "[$(date)] Copied sensor files to /opt/sensor/"
fi

# Setup AWS credentials for Databricks S3 access
if [ -f /opt/deployment/scripts/setup-aws-credentials.sh ]; then
    echo "[$(date)] Running AWS credentials setup script..."
    chmod +x /opt/deployment/scripts/setup-aws-credentials.sh
    /opt/deployment/scripts/setup-aws-credentials.sh
else
    # Fallback to simple credential copy
    if [ -f /opt/deployment/etc/aws/credentials ]; then
        mkdir -p /root/.aws
        cp /opt/deployment/etc/aws/credentials /root/.aws/credentials
        chmod 600 /root/.aws/credentials
        echo "[$(date)] Configured AWS credentials (fallback)"
    fi
fi

# Set proper ownership
chown -R ubuntu:ubuntu /opt/bacalhau
chown -R ubuntu:ubuntu /opt/sensor

# Install Python if not present (needed for node identity generator)
if ! command -v python3 &> /dev/null; then
    echo "[$(date)] Installing Python..."
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip
fi

# Install ec2-metadata tool if not present
if ! command -v ec2-metadata &> /dev/null; then
    echo "[$(date)] Installing ec2-metadata..."
    sudo apt-get install -y cloud-utils
fi

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "[$(date)] Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker ubuntu
    rm get-docker.sh
fi

# Install Docker Compose if not present
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "[$(date)] Installing Docker Compose..."
    sudo apt-get update
    sudo apt-get install -y docker-compose-plugin
fi

# Generate unique node identity for sensor
echo "[$(date)] Generating node identity..."
cd /opt/sensor
if [ -f generate_node_identity.py ]; then
    # Get EC2 instance ID for deterministic identity
    INSTANCE_ID=$(ec2-metadata --instance-id | cut -d ' ' -f 2)
    export INSTANCE_ID
    python3 generate_node_identity.py
    if [ -f config/node_identity.json ]; then
        echo "[$(date)] Node identity generated successfully"
    else
        echo "[$(date)] WARNING: Failed to generate node identity"
    fi
fi

# Pull Docker images
echo "[$(date)] Pulling Docker images..."
docker pull ghcr.io/bacalhau-project/bacalhau:latest
docker pull ghcr.io/bacalhau-project/sensor-log-generator:latest

# Start Bacalhau service
echo "[$(date)] Starting Bacalhau compute node..."
cd /opt/bacalhau
docker compose up -d

# Wait for service to be healthy
echo "[$(date)] Waiting for Bacalhau to be healthy..."
for i in {1..30}; do
    if docker compose ps | grep -q "healthy"; then
        echo "[$(date)] Bacalhau is healthy"
        break
    fi
    echo "[$(date)] Waiting for Bacalhau to start... ($i/30)"
    sleep 10
done

# Show status
docker compose ps
docker compose logs --tail=50

# Start sensor simulator
echo "[$(date)] Starting sensor log generator..."
cd /opt/sensor

# Ensure .env file exists (copy from deployment or create with API keys)
if [ -f /opt/deployment/opt/sensor/.env ]; then
    echo "[$(date)] Copying .env file with API credentials..."
    cp /opt/deployment/opt/sensor/.env .env
else
    echo "[$(date)] Creating .env file with API credentials..."
    cat > .env << 'EOF'
BACALHAU_API_HOST=http://147.135.16.87:1234
BACALHAU_API_KEY=9847fc83-f353-4cf6-8001-b82da00bacf5
GEMINI_API_KEY=AIzaSyAVkKMHfpYI4xgHL1qDtfPIAZCjSXkd8NI
EOF
fi

docker compose up -d

# Wait for sensor to be running
echo "[$(date)] Waiting for sensor to start..."
for i in {1..10}; do
    if docker compose ps | grep -q "Up"; then
        echo "[$(date)] Sensor log generator is running"
        break
    fi
    echo "[$(date)] Waiting for sensor to start... ($i/10)"
    sleep 2
done

# Show status of all services
echo "[$(date)] ========================================="
echo "[$(date)] All services setup complete!"
echo "[$(date)] ========================================="
echo "[$(date)] Bacalhau node connected to orchestrator"
echo "[$(date)] Sensor simulator running on port 8080"
echo ""
echo "[$(date)] Service status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "[$(date)] Check logs:"
echo "  Bacalhau: docker compose -f /opt/bacalhau/docker-compose.yml logs -f"
echo "  Sensor: docker compose -f /opt/sensor/docker-compose.yml logs -f"
echo ""
echo "[$(date)] Sensor data location: /opt/sensor/data/"
