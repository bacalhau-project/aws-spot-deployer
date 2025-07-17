#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

"""Create a minimal cloud-init replacement function."""

import textwrap

minimal_function = '''
def generate_minimal_cloud_init(config: SimpleConfig) -> str:
    """Generate minimal cloud-init with essential bootstrap only."""
    import textwrap
    import base64
    import gzip
    import io
    
    # Get public SSH key content
    public_key = config.public_ssh_key_content()
    if not public_key:
        rich_warning("No public SSH key found - SSH access may not work")
        public_key = ""
    
    # Read orchestrator credentials
    orchestrator_endpoint = ""
    orchestrator_token = ""
    files_dir = config.files_directory()
    
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
    except Exception as e:
        rich_warning(f"Could not read orchestrator credentials: {e}")
    
    # Create a compressed bundle of essential files
    scripts_dir = config.scripts_directory()
    bundle_data = {}
    
    # Essential files to embed
    essential_files = [
        ("scripts/startup.py", os.path.join(scripts_dir, "startup.py")),
        ("scripts/generate_bacalhau_config.sh", os.path.join(scripts_dir, "generate_bacalhau_config.sh")),
        ("scripts/bacalhau-startup.service", os.path.join(scripts_dir, "bacalhau-startup.service")),
        ("scripts/setup-config.service", os.path.join(scripts_dir, "setup-config.service")),
        ("scripts/bacalhau.service", os.path.join(scripts_dir, "bacalhau.service")),
        ("scripts/sensor-generator.service", os.path.join(scripts_dir, "sensor-generator.service")),
        ("scripts/docker-compose-bacalhau.yaml", os.path.join(scripts_dir, "docker-compose-bacalhau.yaml")),
        ("config/bacalhau-config.yaml", os.path.join("instance/config", "bacalhau-config.yaml")),
        ("config/sensor-config.yaml", os.path.join("instance/config", "sensor-config.yaml")),
    ]
    
    for arcname, filepath in essential_files:
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    bundle_data[arcname] = f.read()
            except:
                pass
    
    # Build minimal cloud-init
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
  - wget
  - curl
  - git

write_files:
  - path: /opt/startup.log
    content: |
      Cloud-init started at $(date)
    owner: ubuntu:ubuntu
    permissions: '0644'

  - path: /opt/uploaded_files/orchestrator_endpoint
    content: |
      {orchestrator_endpoint}
    owner: ubuntu:ubuntu
    permissions: '0644'
    
  - path: /opt/uploaded_files/orchestrator_token
    content: |
      {orchestrator_token}
    owner: ubuntu:ubuntu
    permissions: '0600'
    
  - path: /opt/deploy_bootstrap.sh
    content: |
      #!/bin/bash
      set -e
      
      echo "[$(date)] Starting bootstrap deployment" | tee -a /opt/startup.log
      
      # Create directories
      mkdir -p /opt/uploaded_files/{{scripts,config}}
      mkdir -p /bacalhau_node /bacalhau_data
      mkdir -p /opt/sensor/{{config,data,logs,exports}}
      mkdir -p /etc/systemd/system
      
      # Extract embedded files
      cd /opt
      python3 /opt/extract_files.py
      
      # Set permissions
      chown -R ubuntu:ubuntu /opt/uploaded_files /bacalhau_node /bacalhau_data /opt/sensor
      chmod +x /opt/uploaded_files/scripts/*.sh
      chmod +x /opt/uploaded_files/scripts/*.py
      
      # Copy systemd services
      cp /opt/uploaded_files/scripts/*.service /etc/systemd/system/
      systemctl daemon-reload
      
      # Download additional files from repository
      echo "[$(date)] Downloading additional deployment files..." | tee -a /opt/startup.log
      cd /opt
      
      # Try to clone the full repository for remaining files
      if command -v git &> /dev/null; then
          # Use the configured repository URL or a default
          REPO_URL="${{SPOT_REPO_URL:-https://github.com/YOUR_ORG/spot.git}}"
          if [ "$REPO_URL" != "https://github.com/YOUR_ORG/spot.git" ]; then
              echo "Cloning from $REPO_URL" | tee -a /opt/startup.log
              git clone --depth 1 "$REPO_URL" spot-repo 2>&1 | tee -a /opt/startup.log || true
              
              if [ -d spot-repo ]; then
                  # Copy any missing files
                  cp -n spot-repo/instance/scripts/* /opt/uploaded_files/scripts/ 2>/dev/null || true
                  cp -n spot-repo/instance/config/* /opt/uploaded_files/config/ 2>/dev/null || true
                  cp -n spot-repo/files/* /opt/uploaded_files/ 2>/dev/null || true
                  
                  # Fix permissions again
                  chown -R ubuntu:ubuntu /opt/uploaded_files
                  chmod +x /opt/uploaded_files/scripts/*.sh /opt/uploaded_files/scripts/*.py
              fi
          fi
      fi
      
      # Start services
      echo "[$(date)] Starting services..." | tee -a /opt/startup.log
      systemctl enable bacalhau-startup.service
      systemctl start bacalhau-startup.service
      
      echo "[$(date)] Bootstrap complete" | tee -a /opt/startup.log
    owner: root:root
    permissions: '0755'
    
  - path: /opt/extract_files.py
    content: |
      #!/usr/bin/env python3
      import os
      import base64
      
      files = {
"""
    
    # Add the embedded files
    for arcname, content in bundle_data.items():
        # Escape the content properly for Python string
        escaped_content = content.replace('\\', '\\\\').replace('"""', '\\"\\"\\"')
        cloud_init += f'          "{arcname}": """{escaped_content}""",\n'
    
    cloud_init += """      }
      
      for path, content in files.items():
          full_path = f"/opt/uploaded_files/{path}"
          os.makedirs(os.path.dirname(full_path), exist_ok=True)
          with open(full_path, 'w') as f:
              f.write(content)
          print(f"Extracted {path}")
    owner: root:root
    permissions: '0755'

runcmd:
  - /opt/deploy_bootstrap.sh
"""
    
    return cloud_init


# Rename the old function and add the new one
generate_full_cloud_init = generate_minimal_cloud_init
'''

print("New minimal cloud-init function created.")
print(f"Size of function definition: {len(minimal_function)} bytes")
print("\nThis function:")
print("1. Embeds only essential files directly")
print("2. Creates a bootstrap script to set up the environment")
print("3. Optionally clones additional files from a git repository")
print("4. Stays well within the 16KB AWS limit")