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
package_upgrade: true
packages:
  - docker.io
  - docker-compose-plugin
  - python3
  - python3-pip
  - python3-requests
  - python3-yaml
  - python3-boto3
  - python3-rich
  - wget
  - curl
  - jq

write_files:
  - path: /opt/startup.log
    content: |
      Cloud-init started at $(date)
    owner: ubuntu:ubuntu
    permissions: '0644'

  - path: /opt/wait_for_deployment.sh
    content: |
      #!/bin/bash
      set -e
      
      echo "[$(date)] Waiting for deployment bundle..." | tee -a /opt/startup.log
      
      # Create directories
      mkdir -p /opt/uploaded_files
      mkdir -p /bacalhau_node /bacalhau_data
      mkdir -p /opt/sensor/{{config,data,logs,exports}}
      chown -R ubuntu:ubuntu /opt/uploaded_files /bacalhau_node /bacalhau_data /opt/sensor
      
      # Wait for deployment bundle
      WAIT_FILE="/opt/deployment-bundle.tar.gz"
      TIMEOUT=600
      ELAPSED=0
      
      while [ ! -f "$WAIT_FILE" ] && [ $ELAPSED -lt $TIMEOUT ]; do
          echo "[$(date)] Waiting for $WAIT_FILE... ($ELAPSED/$TIMEOUT seconds)" | tee -a /opt/startup.log
          sleep 10
          ELAPSED=$((ELAPSED + 10))
      done
      
      if [ ! -f "$WAIT_FILE" ]; then
          echo "[$(date)] ERROR: Timeout waiting for deployment bundle!" | tee -a /opt/startup.log
          exit 1
      fi
      
      echo "[$(date)] Deployment bundle received! Extracting..." | tee -a /opt/startup.log
      
      # Extract bundle
      cd /opt/uploaded_files
      tar -xzf "$WAIT_FILE"
      
      # Write orchestrator credentials
      echo "{orchestrator_endpoint}" > /opt/uploaded_files/orchestrator_endpoint
      echo "{orchestrator_token}" > /opt/uploaded_files/orchestrator_token
      chmod 600 /opt/uploaded_files/orchestrator_token
      
      # Fix permissions
      chown -R ubuntu:ubuntu /opt/uploaded_files
      chmod +x /opt/uploaded_files/scripts/*.sh 2>/dev/null || true
      chmod +x /opt/uploaded_files/scripts/*.py 2>/dev/null || true
      
      # Install systemd services
      cp /opt/uploaded_files/scripts/*.service /etc/systemd/system/
      systemctl daemon-reload
      
      # Start the main service
      systemctl enable bacalhau-startup.service
      systemctl start bacalhau-startup.service
      
      echo "[$(date)] Services started. Setup complete!" | tee -a /opt/startup.log
    owner: root:root
    permissions: '0755'

  - path: /etc/systemd/system/wait-deployment.service
    content: |
      [Unit]
      Description=Wait for deployment bundle and bootstrap
      After=network-online.target cloud-init.target
      Wants=network-online.target
      
      [Service]
      Type=oneshot
      ExecStart=/opt/wait_for_deployment.sh
      RemainAfterExit=yes
      StandardOutput=journal+console
      StandardError=journal+console
      
      [Install]
      WantedBy=multi-user.target
    owner: root:root
    permissions: '0644'

runcmd:
  - systemctl daemon-reload
  - systemctl enable wait-deployment.service
  - systemctl start wait-deployment.service
"""
    
    return cloud_init