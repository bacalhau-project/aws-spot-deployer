#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

"""Create a patch to replace the cloud-init function with a minimal version."""

patch_content = '''
def generate_minimal_cloud_init(config: SimpleConfig) -> str:
    """Generate minimal cloud-init that embeds only essentials and bootstraps the rest."""
    
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
    
    # Read essential scripts
    scripts_dir = config.scripts_directory()
    startup_script = ""
    generate_config_script = ""
    
    try:
        # Read startup.py
        startup_file = os.path.join(scripts_dir, "startup.py")
        if os.path.exists(startup_file):
            with open(startup_file, 'r') as f:
                startup_script = f.read()
        
        # Read generate_bacalhau_config.sh
        config_script_file = os.path.join(scripts_dir, "generate_bacalhau_config.sh")
        if os.path.exists(config_script_file):
            with open(config_script_file, 'r') as f:
                generate_config_script = f.read()
    except Exception as e:
        rich_warning(f"Could not read essential scripts: {e}")
    
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
  - python3-requests
  - python3-yaml
  - python3-boto3
  - python3-rich
  - wget
  - curl
  - git
  - jq
  - lsb-release

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
    
  - path: /opt/uploaded_files/scripts/startup.py
    content: |
{textwrap.indent(startup_script, '      ')}
    owner: ubuntu:ubuntu
    permissions: '0755'
    
  - path: /opt/uploaded_files/scripts/generate_bacalhau_config.sh
    content: |
{textwrap.indent(generate_config_script, '      ')}
    owner: ubuntu:ubuntu
    permissions: '0755'
    
  - path: /opt/bootstrap_deployment.sh
    content: |
      #!/bin/bash
      set -e
      
      echo "Starting deployment bootstrap at $(date)" | tee -a /opt/startup.log
      
      # Create all required directories
      mkdir -p /opt/uploaded_files/{{scripts,config}}
      mkdir -p /bacalhau_node /bacalhau_data
      mkdir -p /opt/sensor/{{config,data,logs,exports}}
      chown -R ubuntu:ubuntu /opt/uploaded_files /bacalhau_node /bacalhau_data /opt/sensor
      
      # Clone deployment repository for remaining files
      cd /opt
      REPO_URL="${{DEPLOYMENT_REPO_URL:-https://github.com/YOUR_ORG/spot.git}}"
      if [ -n "$REPO_URL" ] && [ "$REPO_URL" != "https://github.com/YOUR_ORG/spot.git" ]; then
          echo "Cloning deployment files from $REPO_URL" | tee -a /opt/startup.log
          git clone "$REPO_URL" deployment-files || echo "Failed to clone repo" | tee -a /opt/startup.log
          
          if [ -d deployment-files ]; then
              # Copy all files to expected locations
              cp -r deployment-files/instance/scripts/* /opt/uploaded_files/scripts/ 2>/dev/null || true
              cp -r deployment-files/instance/config/* /opt/uploaded_files/config/ 2>/dev/null || true
              
              # Fix permissions
              chmod +x /opt/uploaded_files/scripts/*.sh /opt/uploaded_files/scripts/*.py
              chown -R ubuntu:ubuntu /opt/uploaded_files
          fi
      fi
      
      # Download remaining files from S3 if configured
      if [ -n "${{DEPLOYMENT_S3_BUCKET}}" ]; then
          echo "Downloading files from S3 bucket: ${{DEPLOYMENT_S3_BUCKET}}" | tee -a /opt/startup.log
          aws s3 sync "s3://${{DEPLOYMENT_S3_BUCKET}}/spot-deployment/" /opt/uploaded_files/ || true
      fi
      
      # Install systemd services
      for service in bacalhau-startup setup-config bacalhau sensor-generator; do
          if [ -f "/opt/uploaded_files/scripts/${{service}}.service" ]; then
              cp "/opt/uploaded_files/scripts/${{service}}.service" /etc/systemd/system/
              echo "Installed ${{service}}.service" | tee -a /opt/startup.log
          fi
      done
      
      systemctl daemon-reload
      
      # Start the deployment chain
      systemctl enable bacalhau-startup.service
      systemctl start bacalhau-startup.service
      
      echo "Bootstrap complete at $(date)" | tee -a /opt/startup.log
    owner: root:root
    permissions: '0755'

runcmd:
  - echo "Running bootstrap script..." >> /opt/startup.log
  - /opt/bootstrap_deployment.sh
  - echo "Cloud-init complete at $(date)" >> /opt/startup.log
"""
    
    return cloud_init
'''

print("Patch to replace generate_full_cloud_init with generate_minimal_cloud_init:")
print("=" * 80)
print(patch_content)
print("=" * 80)
print("\nTo apply this patch:")
print("1. Replace the generate_full_cloud_init function in deploy_spot.py")
print("2. Add 'import textwrap' at the top of the file")
print("3. Update the function call from generate_full_cloud_init to generate_minimal_cloud_init")
print("4. Set DEPLOYMENT_REPO_URL or DEPLOYMENT_S3_BUCKET environment variables for additional files")