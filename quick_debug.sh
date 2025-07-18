#!/bin/bash
# Quick debug script for spot instance deployment

INSTANCE_IP=$1
SSH_KEY=${SSH_KEY:-~/.ssh/id_ed25519}

if [ -z "$INSTANCE_IP" ]; then
    echo "Usage: $0 <instance-ip>"
    echo "Example: $0 54.123.45.67"
    exit 1
fi

echo "=== Quick Debug for $INSTANCE_IP ==="

echo -e "\n1. Testing SSH connection:"
ssh -i $SSH_KEY -o StrictHostKeyChecking=no -o ConnectTimeout=5 ubuntu@$INSTANCE_IP "echo 'SSH connection successful'"

if [ $? -ne 0 ]; then
    echo "SSH connection failed. Instance may not be ready yet."
    exit 1
fi

echo -e "\n2. Cloud-init status:"
ssh -i $SSH_KEY -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP "cloud-init status --long"

echo -e "\n3. Check for wait service (should not exist with minimal cloud-init):"
ssh -i $SSH_KEY -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP "sudo systemctl status wait-deployment.service 2>&1 | head -5"

echo -e "\n4. Check uploaded files:"
echo "   /tmp/uploaded_files:"
ssh -i $SSH_KEY -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP "find /tmp/uploaded_files -type f 2>/dev/null | wc -l"
echo "   /opt/uploaded_files:"
ssh -i $SSH_KEY -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP "find /opt/uploaded_files -type f 2>/dev/null | wc -l"

echo -e "\n5. Deployment logs:"
ssh -i $SSH_KEY -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP "if [ -f /home/ubuntu/deployment.log ]; then echo '=== ~/deployment.log ==='; tail -10 /home/ubuntu/deployment.log; fi"
ssh -i $SSH_KEY -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP "if [ -f /opt/deployment.log ]; then echo '=== /opt/deployment.log ==='; tail -10 /opt/deployment.log; fi"

echo -e "\n6. Startup log:"
ssh -i $SSH_KEY -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP "if [ -f /opt/startup.log ]; then tail -10 /opt/startup.log; else echo 'No startup.log found'; fi"

echo -e "\n7. Check key directories:"
ssh -i $SSH_KEY -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP "ls -ld /opt/uploaded_files /bacalhau_node /opt/sensor 2>&1 | grep -v 'No such file'"

echo -e "\n8. Systemd services:"
ssh -i $SSH_KEY -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP "systemctl list-units --type=service --all | grep -E '(bacalhau|sensor|setup)' | grep -v '^$'"

echo -e "\n9. Docker status:"
ssh -i $SSH_KEY -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP "docker --version && docker ps -a --format 'table {{.Names}}\t{{.Status}}' 2>/dev/null"

echo -e "\n10. Check if deployment completed:"
ssh -i $SSH_KEY -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP "ls -la /opt/deployment_complete 2>&1"

echo -e "\n=== Summary ==="
echo "Run detailed debug with: ./debug_deployment.sh $INSTANCE_IP"