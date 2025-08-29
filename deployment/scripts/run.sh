#!/bin/bash
# Converted from SkyPilot run commands

set -e

set -e

# Wait for Docker to be ready
timeout=60
while [ $timeout -gt 0 ]; do
  if sudo docker version >/dev/null 2>&1; then
    echo "Docker is ready"
    break
  fi
  echo "Waiting for Docker... ($timeout seconds remaining)"
  sleep 2
  timeout=$((timeout-2))
done

if [ $timeout -le 0 ]; then
  echo "Docker failed to start within timeout"
  exit 1
fi

# Generate Bacalhau configuration from orchestrator credentials
echo "Generating Bacalhau configuration..."
cd /opt/scripts
sudo python3 generate_bacalhau_config.py

# Generate node identity for sensor
echo "Generating node identity..."
cd /opt/sensor
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id 2>/dev/null || echo "unknown-$(date +%s)")
sudo INSTANCE_ID=$INSTANCE_ID python3 /opt/scripts/generate_node_identity.py

# Start Bacalhau compute node
echo "Starting Bacalhau compute node..."
cd /opt/compose
sudo docker compose -f bacalhau-compose.yml up -d

# Wait for Bacalhau to initialize
sleep 10

# Start sensor simulator
echo "Starting sensor simulator..."
sudo docker compose -f sensor-compose.yml up -d

# Final health check
sleep 20
echo "=== Deployment Status ==="
sudo docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo "=== Bacalhau Node Status ==="
sudo docker logs bacalhau-compute --tail 10 2>/dev/null || echo "Bacalhau logs not available yet"

echo "=== Sensor Status ==="
sudo docker logs sensor-simulator --tail 10 2>/dev/null || echo "Sensor logs not available yet"

echo "=== Network Status ==="
netstat -tlnp | grep -E ":(1234|4222|22)\s" || echo "No services found on expected ports"

# Run health check script
/opt/scripts/health_check.sh

echo "Deployment complete! Node is ready for Bacalhau workloads."

# Keep the task alive by tailing logs and monitoring services
echo "=== Keeping cluster alive - monitoring services ==="
while true; do
  echo "$(date): Cluster is running - Bacalhau and sensor services active"

  # Check if Docker containers are still running
  if ! sudo docker ps --filter "status=running" | grep -q bacalhau; then
    echo "WARNING: Bacalhau container not running, restarting..."
    cd /opt/compose && sudo docker compose -f bacalhau-compose.yml up -d
  fi

  if ! sudo docker ps --filter "status=running" | grep -q sensor; then
    echo "WARNING: Sensor container not running, restarting..."
    cd /opt/compose && sudo docker compose -f sensor-compose.yml up -d
  fi

  # Sleep for 5 minutes between checks
  sleep 300
done
