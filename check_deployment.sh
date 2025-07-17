#!/bin/bash
# Quick check of deployment status

INSTANCE_IP=${1:-18.116.87.213}  # Default to first instance
SSH_KEY=${SSH_KEY:-~/.ssh/id_rsa}

echo "Checking deployment on $INSTANCE_IP..."

ssh -i $SSH_KEY -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP << 'EOF'
echo "=== Cloud-init Status ==="
cloud-init status

echo -e "\n=== Startup Log ==="
cat /opt/startup.log 2>/dev/null || echo "No startup log yet"

echo -e "\n=== Deployment Bundle ==="
ls -la /opt/deployment-bundle.tar.gz 2>/dev/null || echo "Bundle not uploaded yet"

echo -e "\n=== Uploaded Files ==="
ls -la /opt/uploaded_files/ 2>/dev/null || echo "No files uploaded yet"

echo -e "\n=== Wait Service Status ==="
sudo systemctl status wait-deployment.service --no-pager -n 5

echo -e "\n=== Docker Status ==="
docker ps -a 2>/dev/null || echo "Docker not running"
EOF