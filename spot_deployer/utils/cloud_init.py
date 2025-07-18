"""Cloud-init configuration generation."""
import os
import tarfile
import tempfile

from ..core.config import SimpleConfig
from .display import rich_warning


def create_deployment_bundle(config: SimpleConfig) -> str:
    """Create a tar.gz bundle of all deployment files."""
    bundle_file = os.path.join(tempfile.gettempdir(), "deployment-bundle.tar.gz")
    
    with tarfile.open(bundle_file, "w:gz") as tar:
        # Add scripts
        scripts_dir = config.scripts_directory()
        if os.path.exists(scripts_dir):
            for file in os.listdir(scripts_dir):
                filepath = os.path.join(scripts_dir, file)
                if os.path.isfile(filepath):
                    tar.add(filepath, arcname=f"scripts/{file}")
        
        # Add configs
        config_dir = "instance/config"
        if os.path.exists(config_dir):
            for file in os.listdir(config_dir):
                filepath = os.path.join(config_dir, file)
                if os.path.isfile(filepath):
                    tar.add(filepath, arcname=f"config/{file}")
        
        # Add user files
        files_dir = config.files_directory()
        if os.path.exists(files_dir):
            for file in os.listdir(files_dir):
                filepath = os.path.join(files_dir, file)
                if os.path.isfile(filepath):
                    tar.add(filepath, arcname=f"{file}")
    
    return bundle_file


def generate_minimal_cloud_init(config: SimpleConfig) -> str:
    """Generate minimal cloud-init script for basic setup only."""
    # Get public SSH key content
    public_key = config.public_ssh_key_content()
    if not public_key:
        rich_warning("No public SSH key found - SSH access may not work")
        public_key = ""
    
    # Create minimal cloud-init script - NO REBOOT, NO COMPLEX SERVICES
    cloud_init_script = f"""#cloud-config

users:
  - name: {config.username()}
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    ssh_authorized_keys:
      - {public_key}
    groups: docker

package_update: true
package_upgrade: true

packages:
  - curl
  - wget
  - unzip
  - git
  - python3
  - python3-pip
  - ca-certificates
  - gnupg
  - lsb-release

runcmd:
  # Just create a basic log file in /tmp for cloud-init status
  - touch /tmp/cloud-init-status.log
  - chmod 666 /tmp/cloud-init-status.log
  
  # Install uv
  - |
    curl -LsSf https://astral.sh/uv/install.sh | sh
    if [ -f /root/.local/bin/uv ]; then
      mv /root/.local/bin/uv /usr/local/bin/uv
      chmod +x /usr/local/bin/uv
      ln -sf /usr/local/bin/uv /usr/bin/uv
    fi
  
  # Install Docker
  - |
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    systemctl enable docker
    systemctl start docker
    usermod -aG docker {config.username()}
  
  # Mark cloud-init complete
  - echo "[$(date)] Cloud-init complete - ready for deployment" > /tmp/cloud-init-complete
  - echo "[$(date)] Ready for file upload and deployment" >> /opt/startup.log
"""
    
    return cloud_init_script


def generate_full_cloud_init(config: SimpleConfig) -> str:
    """Generate minimal cloud-init that waits for deployment bundle."""
    
    # Get public SSH key content
    public_key = config.public_ssh_key_content()
    if not public_key:
        rich_warning("No public SSH key found - SSH access may not work")
        public_key = ""
    
    # Read orchestrator credentials if they exist
    orchestrator_endpoint = ""
    orchestrator_token = ""
    files_dir = config.files_directory()
    
    try:
        endpoint_file = os.path.join(files_dir, "orchestrator_endpoint")
        if os.path.exists(endpoint_file):
            with open(endpoint_file, 'r') as f:
                orchestrator_endpoint = f.read().strip()
                # Ensure proper format
                if orchestrator_endpoint and not orchestrator_endpoint.startswith("nats://"):
                    if ":" not in orchestrator_endpoint:
                        orchestrator_endpoint = f"nats://{orchestrator_endpoint}:4222"
                    else:
                        orchestrator_endpoint = f"nats://{orchestrator_endpoint}"
        
        token_file = os.path.join(files_dir, "orchestrator_token")
        if os.path.exists(token_file):
            with open(token_file, 'r') as f:
                orchestrator_token = f.read().strip()
    except Exception as e:
        rich_warning(f"Could not read orchestrator credentials: {e}")
    
    # Build minimal cloud-init that waits for files
    cloud_init = f"""#cloud-config

users:
  - name: {config.username()}
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    ssh_authorized_keys:
      - {public_key}
    groups: docker

package_update: true
packages:
  - python3
  - python3-pip
  - wget
  - curl
  - jq
  - ca-certificates
  - gnupg
  - lsb-release
  - apt-transport-https
  - software-properties-common

write_files:
  - path: /opt/startup.log
    content: |
      Cloud-init started
    owner: root:root
    permissions: '0666'
  
  - path: /opt/orchestrator_endpoint
    content: |
      {orchestrator_endpoint}
    owner: root:root
    permissions: '0644'
  
  - path: /opt/orchestrator_token
    content: |
      {orchestrator_token}
    owner: root:root
    permissions: '0600'
  
  - path: /opt/setup_deployment.sh
    content: |
      #!/bin/bash
      # This script runs after reboot to set up all services
      
      echo "[$(date)] Starting deployment setup" | tee -a /opt/startup.log
      
      # Extract deployment bundle
      if [ ! -f /opt/deployment-bundle.tar.gz ]; then
        echo "[$(date)] ERROR: Deployment bundle not found!" | tee -a /opt/startup.log
        exit 1
      fi
      
      echo "[$(date)] Extracting deployment bundle..." | tee -a /opt/startup.log
      cd /opt
      tar -xzf deployment-bundle.tar.gz
      
      # Move files to correct locations
      echo "[$(date)] Installing files..." | tee -a /opt/startup.log
      
      # Copy configs
      if [ -d /opt/config ]; then
        mkdir -p /opt/uploaded_files/config
        cp -r /opt/config/* /opt/uploaded_files/config/
      fi
      
      # Copy scripts
      if [ -d /opt/scripts ]; then
        mkdir -p /opt/uploaded_files/scripts
        cp -r /opt/scripts/* /opt/uploaded_files/scripts/
        chmod +x /opt/uploaded_files/scripts/*.sh
        chmod +x /opt/uploaded_files/scripts/*.py
      fi
      
      # Copy credential files
      cp /opt/orchestrator_endpoint /opt/uploaded_files/
      cp /opt/orchestrator_token /opt/uploaded_files/
      chmod 600 /opt/uploaded_files/orchestrator_token
      
      # Create required directories
      mkdir -p /bacalhau_node /bacalhau_data
      mkdir -p /opt/sensor/{{config,data,logs,exports}}
      chown -R ubuntu:ubuntu /opt/uploaded_files /bacalhau_node /bacalhau_data /opt/sensor
      
      # Install systemd services
      echo "[$(date)] Installing systemd services..." | tee -a /opt/startup.log
      cp /opt/uploaded_files/scripts/*.service /etc/systemd/system/ 2>/dev/null || true
      systemctl daemon-reload
      
      # Ensure uv is in PATH for systemd services
      echo 'PATH="/home/ubuntu/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"' >> /etc/environment
      
      # Start services in order
      echo "[$(date)] Starting services..." | tee -a /opt/startup.log
      
      # Start bacalhau-startup first
      systemctl enable bacalhau-startup.service
      systemctl start bacalhau-startup.service
      
      # Wait for startup to complete
      sleep 10
      
      # Check if services are running
      echo "[$(date)] Checking Docker containers..." | tee -a /opt/startup.log
      docker ps | tee -a /opt/startup.log
      
      # Check if bacalhau is running
      if docker ps | grep -q bacalhau; then
        echo "[$(date)] SUCCESS: Bacalhau container is running" | tee -a /opt/startup.log
      else
        echo "[$(date)] WARNING: Bacalhau container not found" | tee -a /opt/startup.log
      fi
      
      echo "[$(date)] Deployment setup complete" | tee -a /opt/startup.log
    owner: root:root
    permissions: '0755'

runcmd:
  # Create required directories
  - mkdir -p /opt/uploaded_files /bacalhau_node /bacalhau_data /opt/sensor
  - chown -R {config.username()}:{config.username()} /opt/uploaded_files /bacalhau_node /bacalhau_data /opt/sensor
  
  # Install Docker
  - curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
  - add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
  - apt-get update
  - apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  - usermod -aG docker {config.username()}
  - systemctl enable docker
  - systemctl start docker
  
  # Mark cloud-init as complete
  - echo "[$(date)] Cloud-init complete - waiting for deployment bundle" | tee -a /opt/startup.log
"""
    
    return cloud_init