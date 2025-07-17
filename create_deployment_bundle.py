#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "boto3",
#     "pyyaml",
# ]
# ///

"""Create deployment bundle for upload to instances."""

import os
import tarfile
import io
import time


def create_deployment_bundle(config, output_file="deployment-bundle.tar.gz"):
    """Create a tar.gz bundle of all deployment files."""
    
    print(f"Creating deployment bundle: {output_file}")
    start_time = time.time()
    
    with tarfile.open(output_file, "w:gz") as tar:
        # Add scripts directory
        scripts_dir = config.scripts_directory()
        if os.path.exists(scripts_dir):
            print(f"Adding scripts from {scripts_dir}")
            for file in os.listdir(scripts_dir):
                filepath = os.path.join(scripts_dir, file)
                if os.path.isfile(filepath):
                    arcname = f"scripts/{file}"
                    tar.add(filepath, arcname=arcname)
                    print(f"  Added: {arcname}")
        
        # Add config directory
        config_dir = "instance/config"
        if os.path.exists(config_dir):
            print(f"Adding configs from {config_dir}")
            for file in os.listdir(config_dir):
                filepath = os.path.join(config_dir, file)
                if os.path.isfile(filepath):
                    arcname = f"config/{file}"
                    tar.add(filepath, arcname=arcname)
                    print(f"  Added: {arcname}")
        
        # Add any additional files from files directory (except credentials)
        files_dir = config.files_directory()
        if os.path.exists(files_dir):
            print(f"Adding additional files from {files_dir}")
            for file in os.listdir(files_dir):
                # Skip credential files as they're embedded in cloud-init
                if file in ["orchestrator_endpoint", "orchestrator_token"]:
                    continue
                filepath = os.path.join(files_dir, file)
                if os.path.isfile(filepath):
                    arcname = f"files/{file}"
                    tar.add(filepath, arcname=arcname)
                    print(f"  Added: {arcname}")
    
    # Get file size
    file_size = os.path.getsize(output_file)
    elapsed = time.time() - start_time
    
    print(f"\nBundle created successfully!")
    print(f"  File: {output_file}")
    print(f"  Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    print(f"  Time: {elapsed:.2f} seconds")
    
    return output_file


def upload_deployment_bundle(hostname, username, private_key_path, bundle_file, logger=None):
    """Upload deployment bundle to instance via SCP."""
    import subprocess
    
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
    
    if logger:
        logger.info(f"Uploading deployment bundle to {hostname}")
    
    try:
        result = subprocess.run(scp_command, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            if logger:
                logger.info(f"Successfully uploaded bundle to {hostname}")
            return True
        else:
            if logger:
                logger.error(f"Failed to upload bundle: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        if logger:
            logger.error("Upload timed out after 60 seconds")
        return False
    except Exception as e:
        if logger:
            logger.error(f"Upload failed: {e}")
        return False


if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from deploy_spot import SimpleConfig
    
    # Test bundle creation
    config = SimpleConfig("config.yaml")
    bundle_file = create_deployment_bundle(config)
    
    print("\nTo upload to an instance:")
    print(f"  scp -i ~/.ssh/your-key.pem {bundle_file} ubuntu@<instance-ip>:/opt/")
    print("\nThe instance will automatically detect and extract this file.")