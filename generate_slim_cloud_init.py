#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pyyaml",
#     "boto3",
# ]
# ///

"""Generate a slim cloud-init that bootstraps from S3 or HTTP."""

def generate_slim_cloud_init(config, bootstrap_url=None):
    """Generate minimal cloud-init that downloads and runs a bootstrap script."""
    
    username = config.username()
    public_key = config.public_ssh_key_content() or ""
    
    # If no bootstrap URL provided, we'll embed a minimal bootstrap script
    if bootstrap_url:
        bootstrap_method = f"wget -O /tmp/bootstrap.sh '{bootstrap_url}' && chmod +x /tmp/bootstrap.sh && /tmp/bootstrap.sh"
    else:
        # Embed minimal bootstrap that pulls everything else
        bootstrap_method = """cat > /tmp/bootstrap.sh << 'BOOTSTRAP_EOF'
#!/bin/bash
set -e

# Create directories
mkdir -p /opt/uploaded_files/{scripts,config}
mkdir -p /bacalhau_node /bacalhau_data
mkdir -p /opt/sensor/{config,data,logs,exports}

# Download deployment package from S3 or GitHub
# Option 1: From S3 (requires IAM role)
# aws s3 cp s3://my-bucket/spot-deployment.tar.gz /tmp/
# tar -xzf /tmp/spot-deployment.tar.gz -C /opt/uploaded_files/

# Option 2: From GitHub release
REPO="your-github-user/spot"
VERSION="latest"
wget -q https://github.com/$REPO/releases/download/$VERSION/deployment-files.tar.gz -O /tmp/deployment.tar.gz
tar -xzf /tmp/deployment.tar.gz -C /opt/uploaded_files/

# Set permissions
chown -R ubuntu:ubuntu /opt/uploaded_files /bacalhau_node /bacalhau_data /opt/sensor
chmod +x /opt/uploaded_files/scripts/*.sh /opt/uploaded_files/scripts/*.py

# Copy systemd services
cp /opt/uploaded_files/scripts/*.service /etc/systemd/system/
systemctl daemon-reload

# Enable and start services
systemctl enable bacalhau-startup.service
systemctl start bacalhau-startup.service

echo "Bootstrap complete at $(date)" >> /opt/startup.log
BOOTSTRAP_EOF

chmod +x /tmp/bootstrap.sh
/tmp/bootstrap.sh"""

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
  - wget
  - curl
  - jq
  - git

write_files:
  - path: /opt/startup.log
    content: |
      Cloud-init started at $(date)
    owner: ubuntu:ubuntu
    permissions: '0644'

runcmd:
  - echo "Starting bootstrap at $(date)" >> /opt/startup.log
  - {bootstrap_method}
  - echo "Bootstrap finished at $(date)" >> /opt/startup.log
"""
    
    return cloud_init


def generate_slim_cloud_init_with_essentials(config):
    """Generate cloud-init with only essential files embedded."""
    
    username = config.username()
    public_key = config.public_ssh_key_content() or ""
    
    # Read only the essential credential files
    files_dir = config.files_directory()
    orchestrator_endpoint = ""
    orchestrator_token = ""
    
    try:
        endpoint_file = os.path.join(files_dir, "orchestrator_endpoint")
        if os.path.exists(endpoint_file):
            with open(endpoint_file, 'r') as f:
                orchestrator_endpoint = f.read().strip()
                
        token_file = os.path.join(files_dir, "orchestrator_token")
        if os.path.exists(token_file):
            with open(token_file, 'r') as f:
                orchestrator_token = f.read().strip()
    except:
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
  - wget
  - curl
  - git

write_files:
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
    
  - path: /opt/bootstrap.sh
    content: |
      #!/bin/bash
      set -e
      
      echo "Starting bootstrap at $(date)" | tee -a /opt/startup.log
      
      # Clone the deployment files
      cd /opt
      git clone https://github.com/YOUR_REPO/spot.git deployment-repo || \\
        (echo "Failed to clone repo" >> /opt/startup.log && exit 1)
      
      # Copy files to expected locations
      cp -r deployment-repo/instance/scripts /opt/uploaded_files/
      cp -r deployment-repo/instance/config /opt/uploaded_files/
      cp -r deployment-repo/files/* /opt/uploaded_files/ 2>/dev/null || true
      
      # Fix permissions
      chown -R ubuntu:ubuntu /opt/uploaded_files
      chmod +x /opt/uploaded_files/scripts/*.sh
      chmod +x /opt/uploaded_files/scripts/*.py
      
      # Create directories
      mkdir -p /bacalhau_node /bacalhau_data
      mkdir -p /opt/sensor/{{config,data,logs,exports}}
      chown -R ubuntu:ubuntu /bacalhau_node /bacalhau_data /opt/sensor
      
      # Install systemd services
      cp /opt/uploaded_files/scripts/*.service /etc/systemd/system/
      systemctl daemon-reload
      
      # Start services
      systemctl enable bacalhau-startup.service
      systemctl start bacalhau-startup.service
      
      echo "Bootstrap complete at $(date)" | tee -a /opt/startup.log
    owner: root:root
    permissions: '0755'

runcmd:
  - /opt/bootstrap.sh
"""
    
    return cloud_init


if __name__ == "__main__":
    import os
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from deploy_spot import SimpleConfig
    
    config = SimpleConfig("config.yaml")
    
    # Test slim version
    slim = generate_slim_cloud_init_with_essentials(config)
    size = len(slim.encode('utf-8'))
    base64_size = size * 4 / 3
    
    print(f"Slim cloud-init size: {size:,} bytes ({size/1024:.1f} KB)")
    print(f"Base64 size: {int(base64_size):,} bytes ({base64_size/1024:.1f} KB)")
    print(f"AWS limit: 16,384 bytes (16.0 KB)")
    print(f"Usage: {(base64_size/16384)*100:.1f}%")
    
    if base64_size < 16384:
        print("✅ Size is within AWS limits!")
    else:
        print("❌ Still too large!")
    
    # Save for inspection
    with open("cloud-init-slim.yaml", "w") as f:
        f.write(slim)