def generate_full_cloud_init(config: SimpleConfig) -> str:
    """Generate minimal cloud-init that waits for deployment bundle."""
    import glob
    import tarfile
    
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
  - docker.io
  - python3
  - python3-pip
  - wget
  - curl
  - jq

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

  - path: /etc/systemd/system/setup-deployment.service
    content: |
      [Unit]
      Description=Setup deployment after reboot
      After=network-online.target docker.service
      Requires=docker.service
      ConditionPathExists=/opt/deployment-bundle.tar.gz
      
      [Service]
      Type=oneshot
      ExecStart=/opt/setup_deployment.sh
      RemainAfterExit=yes
      StandardOutput=journal+console
      StandardError=journal+console
      TimeoutStartSec=600
      
      [Install]
      WantedBy=multi-user.target
    owner: root:root
    permissions: '0644'

runcmd:
  # Wait for deployment bundle upload
  - echo "[$(date)] Waiting for deployment bundle upload..." | tee -a /opt/startup.log
  - |
    TIMEOUT=600
    ELAPSED=0
    while [ ! -f /tmp/UPLOAD_COMPLETE ] && [ $ELAPSED -lt $TIMEOUT ]; do
        echo "[$(date)] Still waiting... ($ELAPSED/$TIMEOUT seconds)" | tee -a /opt/startup.log
        sleep 10
        ELAPSED=$((ELAPSED + 10))
    done
    
    if [ ! -f /tmp/UPLOAD_COMPLETE ]; then
        echo "[$(date)] ERROR: Timeout waiting for upload!" | tee -a /opt/startup.log
        exit 1
    fi
    
    echo "[$(date)] Upload complete marker detected" | tee -a /opt/startup.log
    
    # Move bundle to final location
    if [ -f /tmp/deployment-bundle.tar.gz ]; then
        mv /tmp/deployment-bundle.tar.gz /opt/
        echo "[$(date)] Bundle moved to /opt/" | tee -a /opt/startup.log
    fi
    
    # Enable the setup service to run after reboot
    systemctl enable setup-deployment.service
    echo "[$(date)] Setup service enabled for next boot" | tee -a /opt/startup.log
    
    # Schedule a reboot
    echo "[$(date)] Scheduling reboot in 10 seconds..." | tee -a /opt/startup.log
    shutdown -r +0.2 "Rebooting to complete deployment"
"""
    
    return cloud_init