#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

"""Patch to add two-stage deployment to deploy_spot.py"""

print("""
# Two-Stage Deployment Patch for deploy_spot.py

## 1. Add these imports at the top:
```python
import tarfile
import tempfile
```

## 2. Replace generate_full_cloud_init with this function:
""")

new_function = '''
def generate_full_cloud_init(config: SimpleConfig) -> str:
    """Generate minimal cloud-init that waits for deployment bundle."""
    
    username = config.username()
    public_key = config.public_ssh_key_content() or ""
    
    # Read only the orchestrator credentials
    files_dir = config.files_directory()
    orchestrator_endpoint = ""
    orchestrator_token = ""
    
    try:
        endpoint_file = os.path.join(files_dir, "orchestrator_endpoint")
        if os.path.exists(endpoint_file):
            with open(endpoint_file, 'r') as f:
                orchestrator_endpoint = f.read().strip()
                if orchestrator_endpoint and not orchestrator_endpoint.startswith("nats://"):
                    if ":" not in orchestrator_endpoint:
                        orchestrator_endpoint = f"nats://{orchestrator_endpoint}:4222"
                    else:
                        orchestrator_endpoint = f"nats://{orchestrator_endpoint}"
        
        token_file = os.path.join(files_dir, "orchestrator_token")
        if os.path.exists(token_file):
            with open(token_file, 'r') as f:
                orchestrator_token = f.read().strip()
    except Exception:
        pass
    
    cloud_init = f"""#cloud-config

users:
  - name: {username}
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
'''

print(new_function)

print("""
## 3. Add this function after generate_full_cloud_init:
""")

bundle_functions = '''
def create_deployment_bundle(config: SimpleConfig) -> str:
    """Create a tar.gz bundle of all deployment files."""
    
    bundle_file = "/tmp/deployment-bundle.tar.gz"
    
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
        
        # Add other files (except credentials)
        files_dir = config.files_directory()
        if os.path.exists(files_dir):
            for file in os.listdir(files_dir):
                if file in ["orchestrator_endpoint", "orchestrator_token"]:
                    continue
                filepath = os.path.join(files_dir, file)
                if os.path.isfile(filepath):
                    tar.add(filepath, arcname=f"files/{file}")
    
    return bundle_file


def upload_deployment_bundle(hostname: str, username: str, private_key_path: str, bundle_file: str, logger=None) -> bool:
    """Upload deployment bundle to instance."""
    
    remote_path = "/opt/deployment-bundle.tar.gz"
    
    scp_command = [
        "scp",
        "-i", private_key_path,
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "ConnectTimeout=10",
        bundle_file,
        f"{username}@{hostname}:{remote_path}"
    ]
    
    try:
        result = subprocess.run(scp_command, capture_output=True, text=True, timeout=60)
        return result.returncode == 0
    except:
        return False
'''

print(bundle_functions)

print("""
## 4. Modify the wait_for_instance_ready function to upload the bundle:

Add this after the instance is accessible (around line where it says "Instance accessible"):

```python
                    # Upload deployment bundle
                    update_progress("Upload", 70, "Uploading deployment files...")
                    
                    # Create bundle if not exists
                    if not hasattr(wait_for_instance_ready, '_bundle_created'):
                        bundle_file = create_deployment_bundle(config)
                        wait_for_instance_ready._bundle_created = True
                        wait_for_instance_ready._bundle_file = bundle_file
                    else:
                        bundle_file = wait_for_instance_ready._bundle_file
                    
                    # Upload bundle
                    if upload_deployment_bundle(hostname, username, private_key_path, bundle_file, logger):
                        update_progress("Upload", 85, "Files uploaded successfully")
                    else:
                        update_progress("Upload", 70, "Upload failed, retrying...")
                        continue
```

## 5. Benefits:
- Cloud-init stays under 4KB (well within 16KB limit)
- No external dependencies (S3, HTTP servers)
- Files are pushed by deploy_spot.py after instance is ready
- Instance waits for files then bootstraps automatically
- Clean separation of concerns
""")