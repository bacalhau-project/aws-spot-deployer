#!/bin/bash
# Test 4: Docker Containers and Applications
# Usage: ./debug_test_containers.sh <instance-ip>

set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <instance-ip>"
    exit 1
fi

INSTANCE_IP=$1
SSH_KEY=$(grep ssh_key_path config.yaml 2>/dev/null | awk '{print $2}' | tr -d '"' || echo "~/.ssh/id_rsa")
USERNAME="ubuntu"

echo "=========================================="
echo "Docker Containers Test for $INSTANCE_IP"
echo "=========================================="
echo ""

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$USERNAME@$INSTANCE_IP" 'bash -s' << 'ENDSSH'

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "1. Docker Installation Status"
echo "-----------------------------"
if command -v docker &>/dev/null; then
    docker_version=$(docker --version)
    echo -e "${GREEN}✅${NC} Docker installed: $docker_version"
    
    if docker compose version &>/dev/null; then
        compose_version=$(docker compose version)
        echo -e "${GREEN}✅${NC} Docker Compose: $compose_version"
    else
        echo -e "${RED}❌${NC} Docker Compose plugin not found"
    fi
else
    echo -e "${RED}❌${NC} Docker not installed or not in PATH"
    exit 1
fi

# Check Docker daemon
if docker ps &>/dev/null; then
    echo -e "${GREEN}✅${NC} Docker daemon is running"
else
    echo -e "${RED}❌${NC} Cannot connect to Docker daemon"
    echo "Attempting to start Docker..."
    sudo systemctl start docker 2>&1 || echo "Failed to start Docker"
fi
echo ""

echo "2. Running Containers"
echo "---------------------"
running_containers=$(docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | tail -n +2)
if [ -z "$running_containers" ]; then
    echo -e "${YELLOW}⚠${NC}  No containers are running"
else
    echo "$running_containers"
fi
echo ""

echo "3. All Containers (including stopped)"
echo "-------------------------------------"
all_containers=$(docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}" | tail -n +2)
if [ -z "$all_containers" ]; then
    echo "No containers found"
else
    echo "$all_containers"
fi
echo ""

echo "4. Docker Compose Stack Status"
echo "------------------------------"
echo "Bacalhau Stack:"
if [ -f "/opt/uploaded_files/scripts/docker-compose-bacalhau.yaml" ]; then
    cd /opt/uploaded_files/scripts/ 2>/dev/null || cd /tmp
    docker compose -f /opt/uploaded_files/scripts/docker-compose-bacalhau.yaml ps 2>&1 || echo "Failed to check Bacalhau stack"
else
    echo -e "${RED}❌${NC} docker-compose-bacalhau.yaml not found"
fi
echo ""

echo "Sensor Stack:"
if [ -f "/opt/uploaded_files/scripts/docker-compose-sensor.yaml" ]; then
    docker compose -f /opt/uploaded_files/scripts/docker-compose-sensor.yaml ps 2>&1 || echo "Failed to check Sensor stack"
else
    echo -e "${RED}❌${NC} docker-compose-sensor.yaml not found"
fi
echo ""

echo "5. Container Logs (last 10 lines)"
echo "---------------------------------"
# Check Bacalhau container
if docker ps | grep -q bacalhau; then
    echo "Bacalhau container logs:"
    docker logs bacalhau-node 2>&1 | tail -10 || echo "No logs available"
else
    echo -e "${YELLOW}⚠${NC}  Bacalhau container not running"
fi
echo ""

# Check Sensor container
if docker ps | grep -q sensor; then
    echo "Sensor container logs:"
    docker logs sensor-generator 2>&1 | tail -10 || echo "No logs available"
else
    echo -e "${YELLOW}⚠${NC}  Sensor container not running"
fi
echo ""

echo "6. Docker Networks"
echo "------------------"
docker network ls
echo ""

echo "7. Docker Volumes"
echo "-----------------"
docker volume ls
echo ""

echo "8. Node Identity Check"
echo "----------------------"
if [ -f "/opt/sensor/config/node_identity.json" ]; then
    echo -e "${GREEN}✅${NC} Node identity exists:"
    cat /opt/sensor/config/node_identity.json | python3 -m json.tool 2>/dev/null | head -15 || cat /opt/sensor/config/node_identity.json | head -15
else
    echo -e "${RED}❌${NC} Node identity file not found"
    echo "Checking if identity generation ran..."
    if [ -f "/opt/uploaded_files/scripts/generate_node_identity.py" ]; then
        echo "Identity script exists, attempting manual generation..."
        sudo python3 /opt/uploaded_files/scripts/generate_node_identity.py 2>&1 | head -20
    fi
fi
echo ""

echo "9. Port Availability"
echo "--------------------"
echo "Checking common ports..."
for port in 1234 8080 9090; do
    if netstat -tuln 2>/dev/null | grep -q ":$port "; then
        echo -e "${GREEN}✓${NC} Port $port is in use"
    else
        echo -e "${YELLOW}-${NC} Port $port is not in use"
    fi
done
echo ""

echo "10. Container Resource Usage"
echo "----------------------------"
if docker ps -q | head -1 &>/dev/null; then
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
else
    echo "No running containers to show stats for"
fi
echo ""

echo "Summary"
echo "-------"
running_count=$(docker ps -q | wc -l)
total_count=$(docker ps -aq | wc -l)

if [ $running_count -gt 0 ]; then
    echo -e "${GREEN}✅${NC} $running_count containers running (out of $total_count total)"
else
    echo -e "${RED}❌${NC} No containers are running"
    if [ $total_count -gt 0 ]; then
        echo "   Found $total_count stopped containers"
        echo "   To investigate: docker ps -a"
        echo "   To see logs: docker logs <container-name>"
    else
        echo "   No containers found at all"
        echo "   Services may not have started successfully"
    fi
fi

# Check if we should try to start containers
if [ $running_count -eq 0 ] && [ -f "/opt/uploaded_files/scripts/docker-compose-bacalhau.yaml" ]; then
    echo ""
    echo "Attempting to start containers manually..."
    cd /opt/uploaded_files/scripts/ 2>/dev/null || cd /tmp
    docker compose -f docker-compose-bacalhau.yaml up -d 2>&1 | head -10
    docker compose -f docker-compose-sensor.yaml up -d 2>&1 | head -10
fi

ENDSSH