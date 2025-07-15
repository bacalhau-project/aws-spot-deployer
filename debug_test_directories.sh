#!/bin/bash
# Test 2: Directory and File Structure
# Usage: ./debug_test_directories.sh <instance-ip>

set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <instance-ip>"
    exit 1
fi

INSTANCE_IP=$1
SSH_KEY=$(grep ssh_key_path config.yaml 2>/dev/null | awk '{print $2}' | tr -d '"' || echo "~/.ssh/id_rsa")
USERNAME="ubuntu"

echo "=========================================="
echo "Directory Structure Test for $INSTANCE_IP"
echo "=========================================="
echo ""

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$USERNAME@$INSTANCE_IP" 'bash -s' << 'ENDSSH'

# Color output helpers
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_dir() {
    local dir=$1
    local required=$2
    
    if [ -d "$dir" ]; then
        local perms=$(stat -c "%a" "$dir" 2>/dev/null || stat -f "%p" "$dir" 2>/dev/null | cut -c4-6)
        local owner=$(stat -c "%U:%G" "$dir" 2>/dev/null || stat -f "%Su:%Sg" "$dir" 2>/dev/null)
        if [ "$required" = "required" ]; then
            echo -e "${GREEN}✅${NC} $dir (perms: $perms, owner: $owner)"
        else
            echo -e "${GREEN}✓${NC}  $dir (perms: $perms, owner: $owner)"
        fi
        return 0
    else
        if [ "$required" = "required" ]; then
            echo -e "${RED}❌${NC} $dir MISSING!"
        else
            echo -e "${YELLOW}⚠${NC}  $dir not found (optional)"
        fi
        return 1
    fi
}

check_file() {
    local file=$1
    local required=$2
    
    if [ -f "$file" ]; then
        local size=$(stat -c "%s" "$file" 2>/dev/null || stat -f "%z" "$file" 2>/dev/null)
        local perms=$(stat -c "%a" "$file" 2>/dev/null || stat -f "%p" "$file" 2>/dev/null | cut -c4-6)
        echo -e "${GREEN}✅${NC} $file (${size}B, perms: $perms)"
        return 0
    else
        if [ "$required" = "required" ]; then
            echo -e "${RED}❌${NC} $file MISSING!"
        else
            echo -e "${YELLOW}⚠${NC}  $file not found"
        fi
        return 1
    fi
}

echo "1. Core Directory Structure"
echo "---------------------------"
missing_dirs=0
check_dir "/opt/uploaded_files" "required" || ((missing_dirs++))
check_dir "/opt/uploaded_files/scripts" "required" || ((missing_dirs++))
check_dir "/opt/uploaded_files/config" "required" || ((missing_dirs++))
check_dir "/tmp/exs" "optional"
check_dir "/tmp/uploaded_files" "optional"
check_dir "/bacalhau_node" "required" || ((missing_dirs++))
check_dir "/bacalhau_data" "required" || ((missing_dirs++))
check_dir "/opt/sensor" "required" || ((missing_dirs++))
check_dir "/opt/sensor/config" "required" || ((missing_dirs++))
echo ""

echo "2. Critical Script Files"
echo "------------------------"
missing_scripts=0
check_file "/opt/uploaded_files/scripts/simple-startup.py" "required" || ((missing_scripts++))
check_file "/opt/uploaded_files/scripts/generate_node_identity.py" "required" || ((missing_scripts++))
check_file "/opt/uploaded_files/scripts/setup_bacalhau.py" "optional"
check_file "/opt/uploaded_files/scripts/verify_docker.py" "optional"
echo ""

echo "3. Service Files"
echo "----------------"
missing_services=0
check_file "/opt/uploaded_files/scripts/bacalhau-startup.service" "required" || ((missing_services++))
check_file "/opt/uploaded_files/scripts/setup-config.service" "required" || ((missing_services++))
check_file "/opt/uploaded_files/scripts/bacalhau.service" "required" || ((missing_services++))
check_file "/opt/uploaded_files/scripts/sensor-generator.service" "required" || ((missing_services++))
echo ""

echo "4. SystemD Service Installation"
echo "-------------------------------"
installed_services=0
for service in bacalhau-startup setup-config bacalhau sensor-generator; do
    if [ -f "/etc/systemd/system/${service}.service" ]; then
        echo -e "${GREEN}✅${NC} /etc/systemd/system/${service}.service installed"
        ((installed_services++))
    else
        echo -e "${RED}❌${NC} /etc/systemd/system/${service}.service NOT installed"
    fi
done
echo ""

echo "5. Configuration Files"
echo "----------------------"
check_file "/opt/uploaded_files/config/bacalhau-config.yaml" "required"
check_file "/opt/uploaded_files/config/sensor-config.yaml" "optional"
check_file "/opt/uploaded_files/config/config-template.yaml" "optional"
echo ""

echo "6. Docker Compose Files"
echo "-----------------------"
check_file "/opt/uploaded_files/scripts/docker-compose-bacalhau.yaml" "required"
check_file "/opt/uploaded_files/scripts/docker-compose-sensor.yaml" "required"
echo ""

echo "7. Log Files"
echo "------------"
check_file "/opt/startup.log" "optional"
check_file "/var/log/startup-progress.log" "optional"
echo ""

echo "8. File Count Summary"
echo "---------------------"
if [ -d "/opt/uploaded_files/scripts" ]; then
    script_count=$(ls -1 /opt/uploaded_files/scripts/ 2>/dev/null | wc -l)
    echo "Scripts directory: $script_count files"
    if [ $script_count -gt 0 ]; then
        echo "Recent files:"
        ls -lt /opt/uploaded_files/scripts/ | head -5
    fi
fi
echo ""

if [ -d "/opt/uploaded_files/config" ]; then
    config_count=$(ls -1 /opt/uploaded_files/config/ 2>/dev/null | wc -l)
    echo "Config directory: $config_count files"
fi
echo ""

echo "Summary"
echo "-------"
total_issues=$((missing_dirs + missing_scripts + missing_services))
if [ $total_issues -eq 0 ]; then
    echo -e "${GREEN}✅${NC} All critical directories and files are present"
    if [ $installed_services -eq 4 ]; then
        echo -e "${GREEN}✅${NC} All services are installed in systemd"
    else
        echo -e "${YELLOW}⚠${NC}  Only $installed_services/4 services installed in systemd"
    fi
else
    echo -e "${RED}❌${NC} Missing $total_issues critical items:"
    echo "   - $missing_dirs directories"
    echo "   - $missing_scripts scripts"
    echo "   - $missing_services service files"
fi

ENDSSH