#!/bin/bash
# Deployment debugging script for AWS spot instances

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <instance-ip> [ssh-key-path]"
    echo "Example: $0 52.34.56.78 ~/.ssh/my-key.pem"
    exit 1
fi

INSTANCE_IP="$1"
SSH_KEY="${2:-$HOME/.ssh/id_rsa}"
SSH_USER="ubuntu"

# SSH command helper
ssh_cmd() {
    ssh -o StrictHostKeyChecking=no -i "$SSH_KEY" "$SSH_USER@$INSTANCE_IP" "$@"
}

echo -e "${BLUE}=== AWS Spot Instance Deployment Debugger ===${NC}"
echo -e "Instance: $INSTANCE_IP"
echo -e "SSH Key: $SSH_KEY"
echo ""

# Test SSH connectivity
echo -e "${YELLOW}1. Testing SSH connectivity...${NC}"
if ssh_cmd "echo 'SSH connection successful'" 2>/dev/null; then
    echo -e "${GREEN}✓ SSH connection successful${NC}"
else
    echo -e "${RED}✗ SSH connection failed${NC}"
    exit 1
fi

# Check cloud-init status
echo -e "\n${YELLOW}2. Checking cloud-init status...${NC}"
ssh_cmd "sudo cloud-init status --wait || true" 2>&1 | head -5
ssh_cmd "sudo tail -20 /var/log/cloud-init-output.log 2>/dev/null || echo 'No cloud-init log found'"

# Check if watcher script exists and is running
echo -e "\n${YELLOW}3. Checking deployment watcher script...${NC}"
if ssh_cmd "test -f /usr/local/bin/watch-for-deployment.sh"; then
    echo -e "${GREEN}✓ Watcher script exists${NC}"
    ssh_cmd "ps aux | grep -v grep | grep watch-for-deployment || echo '✗ Watcher script not running'"
    echo -e "\nWatcher script content:"
    ssh_cmd "cat /usr/local/bin/watch-for-deployment.sh" | head -10
else
    echo -e "${RED}✗ Watcher script missing${NC}"
fi

# Check watcher log
echo -e "\n${YELLOW}4. Checking watcher log...${NC}"
if ssh_cmd "test -f /tmp/watcher.log"; then
    echo "Last 20 lines of watcher log:"
    ssh_cmd "tail -20 /tmp/watcher.log"
else
    echo -e "${RED}✗ No watcher log found${NC}"
fi

# Check uploaded files
echo -e "\n${YELLOW}5. Checking uploaded files...${NC}"
if ssh_cmd "test -d /tmp/uploaded_files"; then
    echo -e "${GREEN}✓ Upload directory exists${NC}"
    echo "Contents of /tmp/uploaded_files:"
    ssh_cmd "find /tmp/uploaded_files -type f | head -20"
    
    if ssh_cmd "test -f /tmp/uploaded_files/marker"; then
        echo -e "${GREEN}✓ Marker file exists${NC}"
    else
        echo -e "${RED}✗ Marker file missing${NC}"
    fi
else
    echo -e "${RED}✗ Upload directory missing${NC}"
fi

# Check if deploy_services.py was run
echo -e "\n${YELLOW}6. Checking deployment script execution...${NC}"
if ssh_cmd "test -f ~/deployment.log"; then
    echo -e "${GREEN}✓ Deployment log exists${NC}"
    echo "Last 20 lines of deployment log:"
    ssh_cmd "tail -20 ~/deployment.log"
else
    echo -e "${RED}✗ Deployment log missing (deploy_services.py may not have run)${NC}"
fi

# Check Docker and UV installation
echo -e "\n${YELLOW}7. Checking Docker and UV installation...${NC}"
if ssh_cmd "which docker >/dev/null 2>&1"; then
    echo -e "${GREEN}✓ Docker installed${NC}"
    ssh_cmd "docker --version"
else
    echo -e "${RED}✗ Docker not installed${NC}"
fi

if ssh_cmd "which uv >/dev/null 2>&1"; then
    echo -e "${GREEN}✓ UV installed${NC}"
    ssh_cmd "uv --version"
else
    echo -e "${RED}✗ UV not installed${NC}"
fi

# Check /opt directories
echo -e "\n${YELLOW}8. Checking /opt directories...${NC}"
for dir in /opt/scripts /opt/uploaded_files /opt/sensor/config; do
    if ssh_cmd "test -d $dir"; then
        echo -e "${GREEN}✓ $dir exists${NC}"
    else
        echo -e "${RED}✗ $dir missing${NC}"
    fi
done

# Check systemd services
echo -e "\n${YELLOW}9. Checking systemd services...${NC}"
for service in bacalhau-startup bacalhau sensor; do
    if ssh_cmd "systemctl is-enabled $service >/dev/null 2>&1"; then
        echo -e "${GREEN}✓ $service.service enabled${NC}"
        ssh_cmd "systemctl status $service --no-pager" 2>&1 | head -5
    else
        echo -e "${RED}✗ $service.service not found/enabled${NC}"
    fi
done

# Check startup script output
echo -e "\n${YELLOW}10. Checking startup script output...${NC}"
if ssh_cmd "test -f /opt/startup.log"; then
    echo "Last 20 lines of startup log:"
    ssh_cmd "tail -20 /opt/startup.log"
else
    echo -e "${RED}✗ No startup log found${NC}"
fi

# Check node identity
echo -e "\n${YELLOW}11. Checking node identity generation...${NC}"
if ssh_cmd "test -f /opt/sensor/config/node_identity.json"; then
    echo -e "${GREEN}✓ Node identity exists${NC}"
    ssh_cmd "cat /opt/sensor/config/node_identity.json | head -10"
else
    echo -e "${RED}✗ Node identity missing${NC}"
fi

# Summary and recommendations
echo -e "\n${BLUE}=== Summary ===${NC}"
echo -e "\nCommon issues and fixes:"
echo -e "1. If watcher script is not running:"
echo -e "   ${YELLOW}ssh_cmd 'nohup /usr/local/bin/watch-for-deployment.sh > /tmp/watcher.log 2>&1 &'${NC}"
echo -e "\n2. If marker file is missing but files are uploaded:"
echo -e "   ${YELLOW}ssh_cmd 'touch /tmp/uploaded_files/marker'${NC}"
echo -e "\n3. If deploy_services.py didn't run:"
echo -e "   ${YELLOW}ssh_cmd 'cd /tmp/uploaded_files/scripts && sudo /usr/bin/uv run deploy_services.py'${NC}"
echo -e "\n4. To check all logs at once:"
echo -e "   ${YELLOW}ssh_cmd 'cat /tmp/watcher.log ~/deployment.log /opt/startup.log 2>/dev/null | grep -E \"ERROR|FAIL|error|fail\"'${NC}"