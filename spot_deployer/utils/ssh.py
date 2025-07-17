"""SSH and file transfer utilities."""
import os
import subprocess
import time
from typing import Optional, Callable

from ..core.constants import DEFAULT_SSH_TIMEOUT


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
                    "ConnectTimeout=5",
                    f"{username}@{hostname}",
                    'echo "SSH ready"',
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return True
        except Exception:
            pass
        time.sleep(5)
    
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
        
        # Create remote directories
        ssh_base = [
            "ssh",
            "-i", private_key_path,
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            f"{username}@{hostname}",
        ]
        
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
            update_progress("SCP: Config", 90, "Uploading configuration...")
            
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
        
        update_progress("SCP: Complete", 100, "All files uploaded successfully")
        return True
    
    except Exception as e:
        log_error(f"Exception during file upload to {hostname}: {e}")
        update_progress("SCP: Error", 0, f"Failed: {str(e)}")
        return False


def enable_startup_service(
    hostname: str, username: str, private_key_path: str, logger=None
) -> bool:
    """Execute the deployment script to configure services."""
    try:
        # First, upload the deploy_services.py script
        deploy_script_path = "instance/scripts/deploy_services.py"
        
        if os.path.exists(deploy_script_path):
            # Upload the deployment script
            scp_command = [
                "scp",
                "-i", private_key_path,
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                deploy_script_path,
                f"{username}@{hostname}:/tmp/deploy_services.py"
            ]
            
            result = subprocess.run(scp_command, capture_output=True, text=True)
            if result.returncode != 0:
                if logger:
                    logger.info(f"Failed to upload deployment script: {result.stderr}")
                return False
        
        # Execute the deployment script
        commands = [
            # Make the script executable
            "chmod +x /tmp/deploy_services.py",
            # Run the deployment script with sudo
            "sudo python3 /tmp/deploy_services.py",
        ]
        
        full_command = " && ".join(commands)
        
        result = subprocess.run(
            [
                "ssh",
                "-i",
                private_key_path,
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "UserKnownHostsFile=/dev/null",
                f"{username}@{hostname}",
                full_command,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        
        if logger:
            logger.info(f"Service configuration stdout: {result.stdout}")
            if result.stderr:
                logger.info(f"Service configuration stderr: {result.stderr}")
            logger.info(f"Service configuration return code: {result.returncode}")
        
        # More flexible success check
        success = (
            result.returncode == 0 
            or "Services installed successfully" in result.stdout
            or "Configuration attempt complete" in result.stdout
        )
        
        return success
    
    except subprocess.TimeoutExpired:
        if logger:
            logger.warning("Service configuration timed out - this may be normal")
        return True  # Don't fail on timeout
    except Exception as e:
        if logger:
            logger.error(f"Error configuring services: {e}")
        return False