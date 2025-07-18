"""SSH and file transfer utilities."""
import os
import subprocess
import time
from typing import Optional, Callable

from ..core.constants import DEFAULT_SSH_TIMEOUT
from .bacalhau_config import generate_bacalhau_config_with_credentials


def wait_for_ssh_only(
    hostname: str, username: str, private_key_path: str, timeout: int = DEFAULT_SSH_TIMEOUT
) -> bool:
    """Simple SSH availability check - no cloud-init monitoring."""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            result = subprocess.run(
                [
                    "ssh",
                    "-i",
                    private_key_path,
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "UserKnownHostsFile=/dev/null",
                    "-o",
                    "ConnectTimeout=3",
                    f"{username}@{hostname}",
                    'echo "SSH ready"',
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return True
        except Exception:
            pass
        time.sleep(2)  # Check more frequently
    
    return False


def transfer_files_scp(
    hostname: str,
    username: str,
    private_key_path: str,
    files_directory: str,
    scripts_directory: str,
    config_directory: str = "instance/config",
    progress_callback: Optional[Callable] = None,
    log_function: Optional[Callable] = None,
) -> bool:
    """Transfer files to instance using SCP."""
    
    def update_progress(phase: str, progress: int, status: str = ""):
        if progress_callback:
            progress_callback(phase, progress, status)
    
    def log_message(msg: str):
        if log_function:
            log_function(msg)
    
    def log_error(msg: str):
        if log_function:
            log_function(f"ERROR: {msg}")
    
    try:
        update_progress("SCP: Starting", 10, "Beginning file transfer")
        
        # Create SSH base command
        ssh_base = [
            "ssh",
            "-i", private_key_path,
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            f"{username}@{hostname}",
        ]
        
        # Create directories in /tmp (where ubuntu user has permissions)
        mkdir_cmd = ssh_base + [
            "mkdir -p /tmp/uploaded_files/scripts /tmp/uploaded_files/config"
        ]
        
        result = subprocess.run(mkdir_cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            log_error(f"Failed to create remote directories: {result.stderr}")
            return False
        
        update_progress("SCP: Directories", 20, "Remote directories created")
        
        # Base SCP command
        scp_base = [
            "scp",
            "-r",
            "-i", private_key_path,
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
        ]
        
        # Transfer scripts
        if os.path.exists(scripts_directory):
            update_progress("SCP: Scripts", 40, "Uploading scripts...")
            
            result = subprocess.run(
                scp_base + [
                    f"{scripts_directory}/.",
                    f"{username}@{hostname}:/tmp/uploaded_files/scripts/",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            
            if result.returncode != 0:
                log_error(f"Failed to upload scripts: {result.stderr}")
            else:
                log_message("Scripts uploaded successfully")
            
            update_progress("SCP: Scripts", 60, "Scripts uploaded")
        
        # Transfer user files
        if os.path.exists(files_directory):
            update_progress("SCP: Files", 70, "Uploading user files...")
            
            result = subprocess.run(
                scp_base + [
                    f"{files_directory}/.",
                    f"{username}@{hostname}:/tmp/uploaded_files/",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            
            if result.returncode != 0:
                log_error(f"Failed to upload files: {result.stderr}")
            else:
                log_message("User files uploaded successfully")
            
            update_progress("SCP: Files", 85, "User files uploaded")
        
        # Transfer config files
        if os.path.exists(config_directory):
            update_progress("SCP: Config", 90, "Preparing configuration...")
            
            # First, generate Bacalhau config with injected credentials
            bacalhau_template = os.path.join(config_directory, "config-template.yaml")
            generated_config = generate_bacalhau_config_with_credentials(
                bacalhau_template,
                files_directory=files_directory
            )
            
            # Upload the generated config as bacalhau-config.yaml
            result = subprocess.run(
                scp_base + [
                    generated_config,
                    f"{username}@{hostname}:/tmp/uploaded_files/config/bacalhau-config.yaml",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            if result.returncode != 0:
                log_error(f"Failed to upload Bacalhau config: {result.stderr}")
            else:
                log_message("Bacalhau config with credentials uploaded")
            
            # Clean up temp file
            try:
                os.unlink(generated_config)
            except Exception:
                pass
            
            # Upload other config files
            result = subprocess.run(
                scp_base + [
                    f"{config_directory}/.",
                    f"{username}@{hostname}:/tmp/uploaded_files/config/",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            
            update_progress("SCP: Config Upload", 95, "Config files uploaded")
        
        # Verify files were uploaded
        update_progress("SCP: Verifying", 95, "Verifying upload...")
        
        verify_cmd = ssh_base + [
            "ls -la /tmp/uploaded_files/scripts/deploy_services.py && echo 'Files verified'"
        ]
        
        result = subprocess.run(verify_cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            log_error("Failed to verify uploaded files")
            update_progress("SCP: Error", 0, "Upload verification failed")
            return False
        
        # Count uploaded files
        count_cmd = ssh_base + [
            "find /tmp/uploaded_files -type f | wc -l"
        ]
        
        result = subprocess.run(count_cmd, capture_output=True, text=True, timeout=10)
        file_count = result.stdout.strip() if result.returncode == 0 else "unknown"
        log_message(f"Uploaded {file_count} files to /tmp/uploaded_files")
        
        # Run deployment script directly after upload
        update_progress("SCP: Deploying", 98, f"Starting deployment ({file_count} files)...")
        
        deploy_cmd = ssh_base + [
            "cd /tmp/uploaded_files/scripts && python3 deploy_services.py > /home/ubuntu/deployment.log 2>&1 &"
        ]
        
        result = subprocess.run(deploy_cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            log_error(f"Failed to start deployment: {result.stderr}")
            update_progress("SCP: Error", 0, "Failed to start deployment")
            return False
        else:
            log_message("Deployment started - check ~/deployment.log on instance")
        
        update_progress("SCP: Complete", 100, f"Uploaded {file_count} files, deployment started")
        return True
    
    except Exception as e:
        log_error(f"Exception during file upload to {hostname}: {e}")
        update_progress("SCP: Error", 0, f"Failed: {str(e)}")
        return False


# Note: enable_startup_service has been removed - cloud-init handles deployment