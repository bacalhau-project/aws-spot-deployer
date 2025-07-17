#!/usr/bin/env python3
"""
Deployment script that handles all service setup after file upload.
This script is executed via SSH after files are uploaded to the instance.
"""

import os
import sys
import time
import shutil
import subprocess
from pathlib import Path
import re

def log(message):
    """Log with timestamp"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")
    with open("/opt/deployment.log", "a") as f:
        f.write(f"[{timestamp}] {message}\n")

def run_command(cmd, check=True):
    """Run shell command and return result"""
    log(f"Running: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        if result.stdout:
            log(f"Output: {result.stdout.strip()}")
        return result
    except subprocess.CalledProcessError as e:
        log(f"Error running command: {e}")
        if e.stderr:
            log(f"Error output: {e.stderr}")
        if check:
            raise
        return e

def wait_for_cloud_init():
    """Wait for cloud-init to complete"""
    log("Waiting for cloud-init to complete...")
    result = run_command("cloud-init status --wait", check=False)
    log("Cloud-init completed")

def create_directories():
    """Create all required directories"""
    directories = [
        "/opt/uploaded_files/scripts",
        "/opt/uploaded_files/config", 
        "/bacalhau_node",
        "/bacalhau_data",
        "/opt/sensor/config",
        "/opt/sensor/data"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        os.chown(directory, 1000, 1000)  # ubuntu user
        log(f"Created directory: {directory}")

def move_files():
    """Move files from upload locations to final destinations"""
    # Define file movements
    movements = [
        # Scripts from temporary locations to final location
        ("/tmp/uploaded_files/scripts", "/opt/uploaded_files/scripts"),
        ("/tmp/exs", "/opt/uploaded_files/scripts"),
        
        # Config files
        ("/tmp/uploaded_files/config", "/opt/uploaded_files/config"),
        
        # Service files to systemd
        ("/tmp/exs/*.service", "/etc/systemd/system/"),
        ("/tmp/uploaded_files/scripts/*.service", "/etc/systemd/system/"),
    ]
    
    for source, dest in movements:
        if "*" in source:
            # Handle glob patterns
            import glob
            for file in glob.glob(source):
                if os.path.exists(file):
                    filename = os.path.basename(file)
                    dest_file = os.path.join(dest, filename)
                    shutil.copy2(file, dest_file)
                    log(f"Copied {file} to {dest_file}")
        else:
            # Handle directories
            if os.path.exists(source):
                if os.path.isdir(source):
                    # Copy directory contents
                    for item in os.listdir(source):
                        src_path = os.path.join(source, item)
                        dst_path = os.path.join(dest, item)
                        if os.path.isfile(src_path):
                            shutil.copy2(src_path, dst_path)
                            log(f"Copied {src_path} to {dst_path}")

def setup_services():
    """Install and enable systemd services"""
    # Reload systemd
    run_command("systemctl daemon-reload")
    
    # Define services to enable
    services = [
        "bacalhau-startup.service",
        "setup-config.service", 
        "bacalhau.service",
        "sensor-generator.service"
    ]
    
    for service in services:
        service_file = f"/etc/systemd/system/{service}"
        if os.path.exists(service_file):
            # Set proper permissions
            os.chmod(service_file, 0o644)
            
            # Fix any dependency issues in the service file
            fix_service_dependencies(service_file)
            
            # Enable the service
            run_command(f"systemctl enable {service}")
            log(f"Enabled {service}")
            
            # Start services that should run immediately
            if service in ["setup-config.service", "bacalhau-startup.service"]:
                result = run_command(f"systemctl start {service}", check=False)
                if result.returncode == 0:
                    log(f"Started {service}")
                else:
                    log(f"Warning: Could not start {service} immediately, will start on reboot")

def copy_configuration_files():
    """Copy configuration files to their final locations"""
    config_copies = [
        ("/opt/uploaded_files/config/bacalhau-config.yaml", "/bacalhau_node/config.yaml"),
        ("/opt/uploaded_files/config/sensor-config.yaml", "/opt/sensor/config/sensor-config.yaml"),
    ]
    
    for source, dest in config_copies:
        if os.path.exists(source):
            dest_dir = os.path.dirname(dest)
            Path(dest_dir).mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
            os.chown(dest, 1000, 1000)  # ubuntu user
            log(f"Copied config: {source} to {dest}")


def run_startup_script():
    """Run the main startup script"""
    startup_script = "/opt/uploaded_files/scripts/startup.py"
    if os.path.exists(startup_script):
        log("Running startup.py script...")
        os.chmod(startup_script, 0o755)
        run_command(f"python3 {startup_script}", check=False)

def fix_service_dependencies(service_file):
    """Remove dependencies on configure-services.service from service files"""
    try:
        with open(service_file, 'r') as f:
            content = f.read()
        
        # Remove configure-services.service from After= and Requires= lines
        original_content = content
        content = re.sub(r'(After=.*?)\s*configure-services\.service', r'\1', content)
        content = re.sub(r'(Requires=.*?)\s*configure-services\.service', r'\1', content)
        content = re.sub(r'^Requires=\s*$', '', content, flags=re.MULTILINE)
        
        if content != original_content:
            with open(service_file, 'w') as f:
                f.write(content)
            log(f"Fixed dependencies in {service_file}")
    except Exception as e:
        log(f"Warning: Could not fix dependencies in {service_file}: {e}")

def create_completion_marker():
    """Create a marker file to indicate deployment is complete"""
    marker_file = "/opt/deployment_complete"
    with open(marker_file, "w") as f:
        f.write(f"Deployment completed at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    log(f"Created completion marker: {marker_file}")

def schedule_reboot():
    """Schedule a reboot in 30 seconds"""
    log("Scheduling system reboot in 30 seconds...")
    run_command("shutdown -r +1 'Deployment complete, rebooting system'")

def main():
    """Main deployment logic"""
    try:
        log("=== Starting deployment script ===")
        
        # Wait for cloud-init
        wait_for_cloud_init()
        
        # Create directories
        create_directories()
        
        # Move files to correct locations
        move_files()
        
        # Copy configuration files
        copy_configuration_files()
        
        # Setup systemd services
        setup_services()
        
        # Run the startup script
        run_startup_script()
        
        # Create completion marker
        create_completion_marker()
        
        # Schedule reboot
        schedule_reboot()
        
        log("=== Deployment script completed successfully ===")
        return 0
        
    except Exception as e:
        log(f"ERROR: Deployment failed: {e}")
        import traceback
        log(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())