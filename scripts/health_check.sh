#!/bin/bash
# Health check script for Bacalhau sensor deployment.
# Validates that all services are running correctly.

set -e

echo "=== Bacalhau Sensor Node Health Check ==="
echo "Time: $(date)"
echo "Node: $(hostname)"
echo

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

success_count=0
failure_count=0
warning_count=0

check_result() {
    if [ "$1" -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
        success_count=$((success_count + 1))
    else
        echo -e "${RED}✗${NC} $2"
        failure_count=$((failure_count + 1))
    fi
}

warn_result() {
    echo -e "${YELLOW}⚠${NC} $1"
    warning_count=$((warning_count + 1))
}

# Check Docker daemon
echo "--- Docker Status ---"
if sudo docker version >/dev/null 2>&1; then
    check_result 0 "Docker daemon is running"
else
    check_result 1 "Docker daemon is not running"
fi

# Check Docker containers
echo
echo "--- Container Status ---"
containers=$(sudo docker ps --format "{{.Names}}")

if echo "$containers" | grep -q "bacalhau-compute"; then
    check_result 0 "Bacalhau compute container is running"

    # Check Bacalhau health
    if sudo docker exec bacalhau-compute bacalhau version >/dev/null 2>&1; then
        check_result 0 "Bacalhau service is responsive"
    else
        check_result 1 "Bacalhau service is not responsive"
    fi
else
    check_result 1 "Bacalhau compute container is not running"
fi

if echo "$containers" | grep -q "sensor-simulator"; then
    check_result 0 "Sensor simulator container is running"
else
    check_result 1 "Sensor simulator container is not running"
fi

# Check network connectivity
echo
echo "--- Network Status ---"

# Check if Bacalhau API port is listening
if netstat -tlnp 2>/dev/null | grep -q ":1234 "; then
    check_result 0 "Bacalhau API port (1234) is listening"
else
    check_result 1 "Bacalhau API port (1234) is not listening"
fi

# Check if Bacalhau NATS port is listening
if netstat -tlnp 2>/dev/null | grep -q ":4222 "; then
    check_result 0 "Bacalhau NATS port (4222) is listening"
else
    warn_result "Bacalhau NATS port (4222) is not listening (may be using orchestrator)"
fi

# Check file system status
echo
echo "--- File System Status ---"

# Check if configuration files exist
if [ -f "/etc/bacalhau/config.yaml" ]; then
    check_result 0 "Bacalhau configuration exists"
else
    check_result 1 "Bacalhau configuration missing"
fi

if [ -f "/opt/sensor/config/node_identity.json" ]; then
    check_result 0 "Node identity configuration exists"
else
    check_result 1 "Node identity configuration missing"
fi

# Check data directories
if [ -d "/bacalhau_data" ] && [ -w "/bacalhau_data" ]; then
    check_result 0 "Bacalhau data directory is accessible"
else
    check_result 1 "Bacalhau data directory is not accessible"
fi

if [ -d "/opt/sensor/data" ] && [ -w "/opt/sensor/data" ]; then
    check_result 0 "Sensor data directory is accessible"
else
    check_result 1 "Sensor data directory is not accessible"
fi

# Check disk space
echo
echo "--- Resource Status ---"
disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$disk_usage" -lt 90 ]; then
    check_result 0 "Disk space is adequate ($disk_usage% used)"
else
    check_result 1 "Disk space is critically low ($disk_usage% used)"
fi

# Check memory
mem_available=$(free | awk 'NR==2{printf "%.0f", ($7/$2)*100}')
if [ "$mem_available" -gt 10 ]; then
    check_result 0 "Memory is adequate (${mem_available}% available)"
else
    warn_result "Memory is low (${mem_available}% available)"
fi

# Check orchestrator connectivity (if configured)
echo
echo "--- Orchestrator Connectivity ---"
if [ -f "/opt/credentials/orchestrator_endpoint" ]; then
    endpoint=$(cat /opt/credentials/orchestrator_endpoint 2>/dev/null)
    if [ -n "$endpoint" ]; then
        # Extract hostname/IP from NATS URL
        host=$(echo "$endpoint" | sed -n 's/.*:\/\/\([^:]*\).*/\1/p')
        if [ -n "$host" ] && ping -c 1 -W 3 "$host" >/dev/null 2>&1; then
            check_result 0 "Orchestrator host is reachable ($host)"
        else
            warn_result "Orchestrator host is not reachable or not configured ($host)"
        fi
    else
        warn_result "Orchestrator endpoint is empty"
    fi
else
    warn_result "No orchestrator endpoint configured (standalone mode)"
fi

# Check recent logs for errors
echo
echo "--- Recent Log Analysis ---"
if sudo docker logs bacalhau-compute --tail 50 2>/dev/null | grep -i -E "(error|fatal|panic)" | head -3; then
    warn_result "Errors found in Bacalhau logs (see above)"
else
    check_result 0 "No critical errors in recent Bacalhau logs"
fi

if sudo docker logs sensor-simulator --tail 50 2>/dev/null | grep -i -E "(error|fatal|panic)" | head -3; then
    warn_result "Errors found in sensor logs (see above)"
else
    check_result 0 "No critical errors in recent sensor logs"
fi

# Summary
echo
echo "=== Health Check Summary ==="
echo -e "${GREEN}Passed: $success_count${NC}"
if [ $warning_count -gt 0 ]; then
    echo -e "${YELLOW}Warnings: $warning_count${NC}"
fi
if [ $failure_count -gt 0 ]; then
    echo -e "${RED}Failed: $failure_count${NC}"
fi

echo
if [ $failure_count -eq 0 ]; then
    if [ $warning_count -eq 0 ]; then
        echo -e "${GREEN}✓ All systems operational${NC}"
        exit 0
    else
        echo -e "${YELLOW}⚠ Systems operational with warnings${NC}"
        exit 0
    fi
else
    echo -e "${RED}✗ Critical issues detected${NC}"
    exit 1
fi
