#!/bin/bash
# Test 3: SystemD Services Status and Logs
# Usage: ./debug_test_services.sh <instance-ip>

set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <instance-ip>"
    exit 1
fi

INSTANCE_IP=$1
SSH_KEY=$(grep ssh_key_path config.yaml 2>/dev/null | awk '{print $2}' | tr -d '"' || echo "~/.ssh/id_rsa")
USERNAME="ubuntu"

echo "=========================================="
echo "SystemD Services Test for $INSTANCE_IP"
echo "=========================================="
echo ""

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$USERNAME@$INSTANCE_IP" 'bash -s' << 'ENDSSH'

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_service() {
    local service=$1
    local status=$(systemctl is-active "$service" 2>/dev/null || echo "not-found")
    local enabled=$(systemctl is-enabled "$service" 2>/dev/null || echo "not-found")
    
    case "$status" in
        active)
            echo -e "${GREEN}✅${NC} $service: active (enabled: $enabled)"
            return 0
            ;;
        inactive)
            echo -e "${YELLOW}⚠${NC}  $service: inactive (enabled: $enabled)"
            return 1
            ;;
        failed)
            echo -e "${RED}❌${NC} $service: FAILED (enabled: $enabled)"
            return 2
            ;;
        *)
            echo -e "${RED}❌${NC} $service: not found"
            return 3
            ;;
    esac
}

echo "1. Service Status Overview"
echo "--------------------------"
failed_services=0
inactive_services=0
missing_services=0

for service in bacalhau-startup setup-config bacalhau sensor-generator; do
    check_service "${service}.service"
    case $? in
        0) ;; # active
        1) ((inactive_services++)) ;;
        2) ((failed_services++)) ;;
        3) ((missing_services++)) ;;
    esac
done
echo ""

echo "2. Service Dependencies"
echo "-----------------------"
echo "Checking service order dependencies..."
for service in bacalhau-startup setup-config bacalhau sensor-generator; do
    if systemctl cat "${service}.service" &>/dev/null; then
        echo "${service}:"
        systemctl show -p After -p Requires -p Wants "${service}.service" | grep -v "=$" | sed 's/^/  /'
    fi
done
echo ""

echo "3. Startup Service Log (bacalhau-startup)"
echo "-----------------------------------------"
if systemctl is-active bacalhau-startup.service &>/dev/null; then
    sudo journalctl -u bacalhau-startup.service -n 20 --no-pager
elif [ -f /opt/startup.log ]; then
    echo "Service not active, checking startup.log:"
    tail -20 /opt/startup.log
else
    echo "No logs available"
fi
echo ""

echo "4. Setup Config Service Log"
echo "---------------------------"
sudo journalctl -u setup-config.service -n 15 --no-pager 2>/dev/null || echo "No logs available"
echo ""

echo "5. Service Failure Analysis"
echo "---------------------------"
for service in bacalhau-startup setup-config bacalhau sensor-generator; do
    if systemctl is-failed "${service}.service" &>/dev/null; then
        echo -e "${RED}Failed service: ${service}${NC}"
        echo "Exit code: $(systemctl show -p ExecMainStatus "${service}.service" | cut -d= -f2)"
        echo "Last 5 log lines:"
        sudo journalctl -u "${service}.service" -n 5 --no-pager
        echo ""
    fi
done

echo "6. Service File Verification"
echo "----------------------------"
for service in bacalhau-startup setup-config bacalhau sensor-generator; do
    if [ -f "/etc/systemd/system/${service}.service" ]; then
        echo -e "${GREEN}✓${NC} ${service}.service:"
        # Check key configuration
        grep -E "ExecStart=|After=|Restart=" "/etc/systemd/system/${service}.service" | sed 's/^/  /'
    else
        echo -e "${RED}✗${NC} ${service}.service not found in systemd"
    fi
    echo ""
done

echo "7. Docker Service Check"
echo "-----------------------"
if systemctl is-active docker &>/dev/null; then
    echo -e "${GREEN}✅${NC} Docker service is active"
    docker_version=$(docker --version 2>&1 || echo "Docker command not available")
    echo "   $docker_version"
else
    echo -e "${RED}❌${NC} Docker service is not active"
fi
echo ""

echo "8. Process Check"
echo "----------------"
echo "Python processes:"
ps aux | grep python | grep -v grep | head -5 || echo "No Python processes found"
echo ""
echo "Docker processes:"
ps aux | grep docker | grep -v grep | head -5 || echo "No Docker processes found"
echo ""

echo "9. Manual Service Start Test"
echo "----------------------------"
if [ $failed_services -gt 0 ] || [ $inactive_services -gt 0 ]; then
    echo "Attempting to start inactive/failed services..."
    for service in bacalhau-startup setup-config; do
        status=$(systemctl is-active "${service}.service" 2>/dev/null || echo "not-found")
        if [ "$status" != "active" ] && [ "$status" != "not-found" ]; then
            echo "Starting ${service}.service..."
            sudo systemctl start "${service}.service" 2>&1 || echo "Failed to start"
            sleep 2
            new_status=$(systemctl is-active "${service}.service" 2>/dev/null || echo "failed")
            echo "New status: $new_status"
        fi
    done
fi
echo ""

echo "Summary"
echo "-------"
if [ $missing_services -eq 0 ] && [ $failed_services -eq 0 ] && [ $inactive_services -eq 0 ]; then
    echo -e "${GREEN}✅${NC} All services are installed and active"
else
    echo -e "${RED}Service Issues:${NC}"
    [ $missing_services -gt 0 ] && echo "   - $missing_services services not installed"
    [ $failed_services -gt 0 ] && echo "   - $failed_services services failed"
    [ $inactive_services -gt 0 ] && echo "   - $inactive_services services inactive"
    echo ""
    echo "Troubleshooting steps:"
    echo "1. Check if files were uploaded: ls -la /opt/uploaded_files/scripts/"
    echo "2. Check Docker status: systemctl status docker"
    echo "3. Review service logs: journalctl -u <service-name> -n 50"
fi

ENDSSH