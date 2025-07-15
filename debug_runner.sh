#!/bin/bash
# Automated Debug Runner - Runs all debug tests in sequence
# Usage: ./debug_runner.sh <instance-ip> [--fix]

set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

if [ $# -lt 1 ]; then
    echo "Usage: $0 <instance-ip> [--fix]"
    echo "  --fix: Attempt to fix common issues automatically"
    exit 1
fi

INSTANCE_IP=$1
FIX_MODE=false
if [ $# -gt 1 ] && [ "$2" == "--fix" ]; then
    FIX_MODE=true
fi

SSH_KEY=$(grep ssh_key_path config.yaml 2>/dev/null | awk '{print $2}' | tr -d '"' || echo "~/.ssh/id_rsa")
USERNAME="ubuntu"

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}AWS Spot Instance Debug Runner${NC}"
echo -e "${BLUE}Instance: $INSTANCE_IP${NC}"
echo -e "${BLUE}Fix Mode: $FIX_MODE${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Function to run a test and capture results
run_test() {
    local test_name=$1
    local test_script=$2
    
    echo -e "${YELLOW}Running: $test_name${NC}"
    echo "----------------------------------------"
    
    if [ -f "$test_script" ]; then
        bash "$test_script" "$INSTANCE_IP" 2>&1 | tee "/tmp/debug_${test_name// /_}.log"
        local exit_code=${PIPESTATUS[0]}
        if [ $exit_code -eq 0 ]; then
            echo -e "${GREEN}✅ $test_name completed${NC}"
        else
            echo -e "${RED}❌ $test_name failed (exit code: $exit_code)${NC}"
        fi
    else
        echo -e "${RED}❌ Test script not found: $test_script${NC}"
    fi
    echo ""
    return $exit_code
}

# Quick connectivity test
echo -e "${YELLOW}Testing SSH connectivity...${NC}"
if ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10 "$USERNAME@$INSTANCE_IP" "echo 'SSH connection successful'" 2>/dev/null; then
    echo -e "${GREEN}✅ SSH connection successful${NC}"
else
    echo -e "${RED}❌ Cannot connect to instance via SSH${NC}"
    echo "Please check:"
    echo "  - Instance is running: uv run -s deploy_spot.py list"
    echo "  - Security group allows SSH (port 22)"
    echo "  - SSH key path is correct: $SSH_KEY"
    exit 1
fi
echo ""

# Create test report directory
REPORT_DIR="debug_report_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$REPORT_DIR"

# Run all debug tests
echo -e "${BLUE}Starting comprehensive debug tests...${NC}"
echo ""

# Test 1: Cloud-Init
if ! run_test "Cloud-Init Status" "./debug_test_cloud_init.sh"; then
    echo -e "${YELLOW}⚠ Cloud-init may have issues${NC}"
fi

# Test 2: Directories and Files
if ! run_test "Directory Structure" "./debug_test_directories.sh"; then
    echo -e "${YELLOW}⚠ File upload may have failed${NC}"
fi

# Test 3: Services
if ! run_test "SystemD Services" "./debug_test_services.sh"; then
    echo -e "${YELLOW}⚠ Services are not running properly${NC}"
fi

# Test 4: Docker Containers
if ! run_test "Docker Containers" "./debug_test_containers.sh"; then
    echo -e "${YELLOW}⚠ Containers are not running${NC}"
fi

# Quick summary from instance
echo -e "${BLUE}Quick Status Summary${NC}"
echo "----------------------------------------"
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$USERNAME@$INSTANCE_IP" 'bash -s' << 'ENDSSH' | tee "$REPORT_DIR/summary.txt"
echo "=== System Status ==="
echo "Uptime: $(uptime)"
echo ""
echo "=== Directory Check ==="
[ -d "/opt/uploaded_files/scripts" ] && echo "✅ Scripts uploaded" || echo "❌ Scripts missing"
[ -d "/opt/sensor/config" ] && echo "✅ Sensor config dir exists" || echo "❌ Sensor config missing"
echo ""
echo "=== Service Status ==="
for svc in bacalhau-startup setup-config bacalhau sensor-generator; do
    status=$(systemctl is-active $svc.service 2>/dev/null || echo "not-found")
    case $status in
        active) echo "✅ $svc: active" ;;
        inactive) echo "⚠ $svc: inactive" ;;
        failed) echo "❌ $svc: failed" ;;
        *) echo "❌ $svc: not installed" ;;
    esac
done
echo ""
echo "=== Docker Status ==="
if docker --version &>/dev/null; then
    echo "✅ Docker installed"
    running=$(docker ps -q | wc -l)
    echo "   Running containers: $running"
else
    echo "❌ Docker not working"
fi
echo ""
echo "=== Node Identity ==="
[ -f "/opt/sensor/config/node_identity.json" ] && echo "✅ Node identity generated" || echo "❌ Node identity missing"
ENDSSH

# Auto-fix mode
if [ "$FIX_MODE" == "true" ]; then
    echo ""
    echo -e "${BLUE}Attempting automatic fixes...${NC}"
    echo "----------------------------------------"
    
    ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$USERNAME@$INSTANCE_IP" 'bash -s' << 'ENDSSH'
    echo "1. Fixing Docker installation..."
    if ! docker --version &>/dev/null; then
        sudo dpkg --configure -a
        sudo apt-get update
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io
        sudo systemctl start docker
        sudo systemctl enable docker
        sudo usermod -aG docker ubuntu
    fi
    
    echo ""
    echo "2. Creating missing directories..."
    sudo mkdir -p /opt/uploaded_files/scripts /opt/uploaded_files/config
    sudo mkdir -p /bacalhau_node /bacalhau_data
    sudo mkdir -p /opt/sensor/config
    sudo chown -R ubuntu:ubuntu /opt/uploaded_files /opt/sensor
    
    echo ""
    echo "3. Restarting failed services..."
    for svc in bacalhau-startup setup-config; do
        if systemctl is-failed $svc.service &>/dev/null; then
            echo "Restarting $svc..."
            sudo systemctl reset-failed $svc.service
            sudo systemctl start $svc.service
        fi
    done
    
    echo ""
    echo "4. Checking for manual fixes needed..."
    if [ ! -f "/opt/uploaded_files/scripts/simple-startup.py" ]; then
        echo "❌ Scripts not uploaded - need to re-run deployment"
    fi
    
    if [ ! -f "/etc/systemd/system/bacalhau-startup.service" ]; then
        echo "❌ Service files not installed - cloud-init may have failed"
    fi
ENDSSH
fi

# Generate report
echo ""
echo -e "${BLUE}Generating Debug Report...${NC}"
echo "========================================" > "$REPORT_DIR/debug_report.txt"
echo "Debug Report for $INSTANCE_IP" >> "$REPORT_DIR/debug_report.txt"
echo "Generated: $(date)" >> "$REPORT_DIR/debug_report.txt"
echo "========================================" >> "$REPORT_DIR/debug_report.txt"
echo "" >> "$REPORT_DIR/debug_report.txt"

# Collect all logs
for log in /tmp/debug_*.log; do
    if [ -f "$log" ]; then
        test_name=$(basename "$log" .log | sed 's/debug_//')
        echo "=== $test_name ===" >> "$REPORT_DIR/debug_report.txt"
        grep -E "(✅|❌|⚠|Summary)" "$log" >> "$REPORT_DIR/debug_report.txt" || true
        echo "" >> "$REPORT_DIR/debug_report.txt"
    fi
done

# Final recommendations
echo "" >> "$REPORT_DIR/debug_report.txt"
echo "=== Recommendations ===" >> "$REPORT_DIR/debug_report.txt"

# Check common issues and provide recommendations
if grep -q "Scripts missing" "$REPORT_DIR/summary.txt"; then
    echo "1. Scripts were not uploaded successfully:" >> "$REPORT_DIR/debug_report.txt"
    echo "   - Check SSH connectivity during deployment" >> "$REPORT_DIR/debug_report.txt"
    echo "   - Verify files exist in instance/scripts/ directory" >> "$REPORT_DIR/debug_report.txt"
    echo "   - Consider re-running: uv run -s deploy_spot.py create" >> "$REPORT_DIR/debug_report.txt"
fi

if grep -q "Docker not working" "$REPORT_DIR/summary.txt"; then
    echo "2. Docker installation failed:" >> "$REPORT_DIR/debug_report.txt"
    echo "   - Run: ./fix_docker.sh" >> "$REPORT_DIR/debug_report.txt"
    echo "   - Or use --fix flag with this script" >> "$REPORT_DIR/debug_report.txt"
fi

if grep -q "failed" "$REPORT_DIR/summary.txt"; then
    echo "3. Services have failed:" >> "$REPORT_DIR/debug_report.txt"
    echo "   - Check individual service logs with journalctl" >> "$REPORT_DIR/debug_report.txt"
    echo "   - Verify all dependencies are met" >> "$REPORT_DIR/debug_report.txt"
    echo "   - Try manual service restart" >> "$REPORT_DIR/debug_report.txt"
fi

echo ""
echo -e "${GREEN}Debug report saved to: $REPORT_DIR/${NC}"
echo ""
echo "Key files generated:"
echo "  - $REPORT_DIR/debug_report.txt    # Full report"
echo "  - $REPORT_DIR/summary.txt         # Quick summary"
echo "  - /tmp/debug_*.log                # Individual test logs"
echo ""

# Show quick action items
echo -e "${BLUE}Quick Action Items:${NC}"
if grep -q "Scripts missing" "$REPORT_DIR/summary.txt"; then
    echo -e "${RED}1. Re-run deployment - files were not uploaded${NC}"
elif grep -q "Docker not working" "$REPORT_DIR/summary.txt"; then
    echo -e "${YELLOW}2. Fix Docker: ./debug_runner.sh $INSTANCE_IP --fix${NC}"
elif grep -q "failed" "$REPORT_DIR/summary.txt"; then
    echo -e "${YELLOW}3. Check service logs for specific errors${NC}"
else
    echo -e "${GREEN}✅ Instance appears to be working correctly${NC}"
fi