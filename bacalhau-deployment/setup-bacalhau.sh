#!/bin/bash
# Setup script for Bacalhau compute node

set -e

echo "[$(date)] Setting up Bacalhau compute node..."

# Create directories
mkdir -p /opt/bacalhau
mkdir -p /var/log/bacalhau

# Copy configuration files from extracted tarball
cp /opt/deployment/bacalhau-deployment/bacalhau-config.yaml /opt/bacalhau/config.yaml
cp /opt/deployment/bacalhau-deployment/docker-compose.yml /opt/bacalhau/docker-compose.yml

# Set proper ownership
chown -R ubuntu:ubuntu /opt/bacalhau

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

# Pull Bacalhau image
echo "[$(date)] Pulling Bacalhau Docker image..."
docker pull ghcr.io/bacalhau-project/bacalhau:latest

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

echo "[$(date)] Bacalhau compute node setup complete!"
echo "[$(date)] Node should now be connected to orchestrator at 147.135.16.87"
echo "[$(date)] Check logs with: docker compose -f /opt/bacalhau/docker-compose.yml logs -f"