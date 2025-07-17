#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pyyaml",
#     "boto3",
# ]
# ///

"""Generate cloud-init with compressed embedded files."""

import os
import sys
import gzip
import base64
import tarfile
import io

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from deploy_spot import SimpleConfig


def create_compressed_payload(config):
    """Create a compressed tar.gz of all deployment files."""
    buffer = io.BytesIO()
    
    with tarfile.open(fileobj=buffer, mode='w:gz') as tar:
        # Add scripts
        scripts_dir = config.scripts_directory()
        if os.path.exists(scripts_dir):
            for file in os.listdir(scripts_dir):
                filepath = os.path.join(scripts_dir, file)
                if os.path.isfile(filepath):
                    tar.add(filepath, arcname=f"scripts/{file}")
        
        # Add configs
        instance_config_dir = "instance/config"
        if os.path.exists(instance_config_dir):
            for file in os.listdir(instance_config_dir):
                filepath = os.path.join(instance_config_dir, file)
                if os.path.isfile(filepath):
                    tar.add(filepath, arcname=f"config/{file}")
        
        # Add credential files
        files_dir = config.files_directory()
        for cred_file in ["orchestrator_endpoint", "orchestrator_token"]:
            filepath = os.path.join(files_dir, cred_file)
            if os.path.exists(filepath):
                tar.add(filepath, arcname=f"files/{cred_file}")
    
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode('utf-8')


def generate_compressed_cloud_init(config):
    """Generate cloud-init with compressed embedded files."""
    
    username = config.username()
    public_key = config.public_ssh_key_content() or ""
    
    # Create compressed payload
    compressed_payload = create_compressed_payload(config)
    
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
  - curl
  - git

write_files:
  - path: /opt/deployment.tar.gz.b64
    content: |
      {compressed_payload}
    owner: ubuntu:ubuntu
    permissions: '0644'
    
  - path: /opt/startup.log
    content: |
      Cloud-init started at $(date)
    owner: ubuntu:ubuntu
    permissions: '0644'

runcmd:
  - echo "Extracting deployment files..." >> /opt/startup.log
  - base64 -d /opt/deployment.tar.gz.b64 > /opt/deployment.tar.gz
  - mkdir -p /opt/uploaded_files
  - tar -xzf /opt/deployment.tar.gz -C /opt/uploaded_files/
  - chown -R ubuntu:ubuntu /opt/uploaded_files
  - chmod +x /opt/uploaded_files/scripts/*.sh /opt/uploaded_files/scripts/*.py
  - mkdir -p /bacalhau_node /bacalhau_data /opt/sensor/{{config,data,logs,exports}}
  - chown -R ubuntu:ubuntu /bacalhau_node /bacalhau_data /opt/sensor
  - cp /opt/uploaded_files/scripts/*.service /etc/systemd/system/
  - systemctl daemon-reload
  - systemctl enable bacalhau-startup.service
  - systemctl start bacalhau-startup.service
  - echo "Deployment complete at $(date)" >> /opt/startup.log
"""
    
    return cloud_init


if __name__ == "__main__":
    config = SimpleConfig("config.yaml")
    
    # Test compressed version
    compressed = generate_compressed_cloud_init(config)
    size = len(compressed.encode('utf-8'))
    base64_size = size * 4 / 3
    
    print(f"Compressed cloud-init size: {size:,} bytes ({size/1024:.1f} KB)")
    print(f"Estimated base64 size: {int(base64_size):,} bytes ({base64_size/1024:.1f} KB)")
    print(f"AWS limit: 16,384 bytes (16.0 KB)")
    print(f"Usage: {(base64_size/16384)*100:.1f}%")
    
    if base64_size < 16384:
        print("✅ Size is within AWS limits!")
    else:
        print("❌ Still too large! Need external hosting.")
    
    # Save for inspection
    with open("cloud-init-compressed.yaml", "w") as f:
        f.write(compressed)