# AWS Spot Instance Deployment Debug Checklist

A targeted, step-by-step checklist to debug deployment issues where machines provision but services don't work end-to-end.

## Phase 1: Initial Connection and Cloud-Init Status

### Test 1.1: SSH Connection
```bash
# Get instance info
uv run -s deploy_spot.py list

# SSH to instance
ssh -i ~/.ssh/<your-key>.pem ubuntu@<instance-ip>
```

### Test 1.2: Cloud-Init Completion
```bash
# Run immediately after SSH
sudo cloud-init status --wait
# Expected: "status: done" (if still running, wait)

# Check status file
cat /tmp/cloud-init-status
# Expected: Shows completed steps

# Check for errors
sudo grep -i error /var/log/cloud-init-output.log | head -20
# Expected: No critical errors
```

## Phase 2: Directory and File Structure

### Test 2.1: Critical Directories
```bash
# Check all required directories exist
for dir in /opt/uploaded_files /opt/uploaded_files/scripts /opt/uploaded_files/config /tmp/exs /bacalhau_node /bacalhau_data /opt/sensor/config; do
  if [ -d "$dir" ]; then
    echo "✓ $dir exists"
    ls -ld "$dir"
  else
    echo "✗ $dir MISSING"
  fi
done
```

### Test 2.2: File Upload Verification
```bash
# Check uploaded scripts
echo "=== Scripts ==="
ls -la /opt/uploaded_files/scripts/ | grep -E '(simple-startup|generate_node_identity|docker-compose)'

# Check uploaded configs
echo "=== Configs ==="
ls -la /opt/uploaded_files/config/

# Check service files in systemd
echo "=== Service Files ==="
ls -la /etc/systemd/system/ | grep -E '(bacalhau|sensor|setup)'
```

## Phase 3: Docker Installation

### Test 3.1: Docker Status
```bash
# Check Docker installation
docker --version
# Expected: Docker version 2x.x.x

docker compose version
# Expected: Docker Compose version vx.x.x

# Check Docker service
sudo systemctl status docker
# Expected: active (running)

# Test Docker
sudo docker run hello-world
# Expected: "Hello from Docker!" message
```

### Test 3.2: Docker Group Membership
```bash
# Check user groups
groups ubuntu
# Expected: Should include "docker"

# If not in docker group, check if it was added
getent group docker
# Expected: docker:x:xxx:ubuntu
```

## Phase 4: SystemD Services

### Test 4.1: Service Installation
```bash
# Check all services are installed and enabled
for service in bacalhau-startup setup-config bacalhau sensor-generator; do
  echo "=== $service.service ==="
  systemctl is-enabled $service.service 2>/dev/null && echo "✓ Enabled" || echo "✗ Not enabled"
  systemctl status $service.service --no-pager | head -3
  echo
done
```

### Test 4.2: Service Logs
```bash
# Check startup service (runs first)
sudo journalctl -u bacalhau-startup.service -n 20 --no-pager

# Check setup-config service (runs second)
sudo journalctl -u setup-config.service -n 20 --no-pager

# Check main services
sudo journalctl -u bacalhau.service -n 10 --no-pager
sudo journalctl -u sensor-generator.service -n 10 --no-pager
```

## Phase 5: Startup Script Execution

### Test 5.1: Script Availability
```bash
# Check startup script
ls -la /opt/uploaded_files/scripts/simple-startup.py
# Expected: File exists with read permissions

# Check Python
python3 --version
# Expected: Python 3.x.x

# Check startup log
if [ -f /opt/startup.log ]; then
  echo "Startup log exists:"
  tail -20 /opt/startup.log
else
  echo "✗ No startup log found!"
fi
```

### Test 5.2: Manual Execution Test
```bash
# Try running startup script manually
sudo -u ubuntu python3 /opt/uploaded_files/scripts/simple-startup.py
# Expected: Should complete without errors
```

## Phase 6: Configuration Files and Node Identity

### Test 6.1: Configuration Files
```bash
# Check Bacalhau config
if [ -f /bacalhau_node/config.yaml ]; then
  echo "✓ Bacalhau config exists"
  head -5 /bacalhau_node/config.yaml
else
  echo "✗ Bacalhau config MISSING"
fi

# Check sensor config
if [ -f /opt/sensor/config/sensor-config.yaml ]; then
  echo "✓ Sensor config exists"
  head -5 /opt/sensor/config/sensor-config.yaml
else
  echo "✗ Sensor config MISSING"
fi
```

### Test 6.2: Node Identity
```bash
# Check node identity
if [ -f /opt/sensor/config/node_identity.json ]; then
  echo "✓ Node identity exists:"
  cat /opt/sensor/config/node_identity.json | python3 -m json.tool | head -20
else
  echo "✗ Node identity MISSING"
fi
```

## Phase 7: Docker Containers

### Test 7.1: Container Status
```bash
# Check running containers
docker ps
# Expected: Should show bacalhau and sensor containers

# Check all containers (including stopped)
docker ps -a
# Expected: Look for exit codes if containers stopped

# Check Docker compose status
echo "=== Bacalhau Stack ==="
docker compose -f /opt/uploaded_files/scripts/docker-compose-bacalhau.yaml ps

echo "=== Sensor Stack ==="
docker compose -f /opt/uploaded_files/scripts/docker-compose-sensor.yaml ps
```

### Test 7.2: Container Logs
```bash
# If containers are running, check logs
docker logs bacalhau-node 2>&1 | tail -20
docker logs sensor-generator 2>&1 | tail -20
```

## Quick One-Liner Debug

```bash
# Run this for immediate overview
echo "=== System Info ===" && uptime && echo -e "\n=== Cloud-Init ===" && sudo cloud-init status && echo -e "\n=== Directories ===" && ls -ld /opt/uploaded_files/scripts 2>&1 && echo -e "\n=== Docker ===" && docker --version 2>&1 && docker ps && echo -e "\n=== Services ===" && systemctl status bacalhau-startup setup-config --no-pager | grep -E "(Active:|Main PID)" && echo -e "\n=== Startup Log ===" && tail -5 /opt/startup.log 2>&1
```

## Common Failure Patterns

### Pattern 1: Cloud-Init Timeout
**Symptoms**: "Waiting for service files..." in cloud-init log, services not installed
**Fix**: File upload took too long, increase timeout or check network

### Pattern 2: Docker Not Ready
**Symptoms**: "Cannot connect to Docker daemon" errors
**Fix**: Run `./fix_docker.sh` or wait for cloud-init to complete

### Pattern 3: Services Failed to Start
**Symptoms**: Services show "failed" status
**Fix**: Check service logs with journalctl, verify file paths

### Pattern 4: Missing Directories
**Symptoms**: "/opt/uploaded_files: No such file or directory"
**Fix**: Cloud-init failed early, check cloud-init-output.log

### Pattern 5: Permission Denied
**Symptoms**: "Permission denied" in service logs
**Fix**: Check file ownership and executable bits

## Automated Debug Script

Save this as `debug_instance.sh` and run with instance IP:

```bash
#!/bin/bash
# Usage: ./debug_instance.sh <instance-ip>

if [ $# -ne 1 ]; then
  echo "Usage: $0 <instance-ip>"
  exit 1
fi

IP=$1
SSH_KEY=$(grep ssh_key_path config.yaml | awk '{print $2}' | tr -d '"')

echo "Debugging instance at $IP..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no ubuntu@$IP 'bash -s' << 'EOF'
echo "=== PHASE 1: Cloud-Init ==="
sudo cloud-init status
echo

echo "=== PHASE 2: Directories ==="
for dir in /opt/uploaded_files/scripts /opt/uploaded_files/config /bacalhau_node /opt/sensor/config; do
  [ -d "$dir" ] && echo "✓ $dir" || echo "✗ $dir MISSING"
done
echo

echo "=== PHASE 3: Docker ==="
docker --version 2>&1
docker ps
echo

echo "=== PHASE 4: Services ==="
for svc in bacalhau-startup setup-config bacalhau sensor-generator; do
  systemctl is-active $svc.service
done
echo

echo "=== PHASE 5: Logs ==="
[ -f /opt/startup.log ] && tail -10 /opt/startup.log || echo "No startup log"
echo

echo "=== PHASE 6: Quick Fix Attempt ==="
if ! docker --version &>/dev/null; then
  echo "Docker not working, attempting fix..."
  sudo dpkg --configure -a
  sudo apt-get update && sudo apt-get install -y docker-ce
  sudo systemctl start docker
fi
EOF
```

## Next Steps After Debug

1. **If cloud-init failed**: Check security groups, AMI compatibility
2. **If directories missing**: Re-run deployment with longer timeouts
3. **If Docker broken**: Run fix_docker.sh script
4. **If services failed**: Check individual service logs and file paths
5. **If all looks good but not working**: Check container logs for application errors