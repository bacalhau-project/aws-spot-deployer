#!/usr/bin/env uv run
"""
Deployment script that handles all service setup after file upload.
This script is executed via SSH after files are uploaded to the instance.
"""

import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


def log(message):
    """Log with timestamp"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")
    # Write to /opt/deployment.log for compatibility and to home dir for access
    log_paths = ["/opt/deployment.log", "/home/ubuntu/deployment.log"]
    for log_path in log_paths:
        try:
            with open(log_path, "a") as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception:
            pass  # Ignore permission errors


def run_command(cmd, check=True):
    """Run shell command and return result"""
    log(f"Running: {cmd}")
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, check=check
        )
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


def create_directories():
    """Create all required directories with sudo"""
    directories = [
        "/opt/uploaded_files/scripts",
        "/opt/uploaded_files/config",
        "/bacalhau_node",
        "/bacalhau_data",
        # Sensor directories are now created by additional_commands.sh
    ]

    for directory in directories:
        try:
            # Create directory with sudo
            run_command(f"sudo mkdir -p {directory}")
            # Set ownership to ubuntu user
            run_command(f"sudo chown ubuntu:ubuntu {directory}")
            log(f"Created directory: {directory}")
        except Exception as e:
            log(f"Error creating {directory}: {e}")


def move_files():
    """Move files from /tmp upload location to final destinations"""
    # First, move everything from /tmp to /opt
    if os.path.exists("/tmp/uploaded_files"):
        log("Moving files from /tmp/uploaded_files to /opt/uploaded_files")
        try:
            # Use sudo to move files to /opt
            run_command("sudo mv /tmp/uploaded_files/* /opt/uploaded_files/")
            run_command("sudo chown -R ubuntu:ubuntu /opt/uploaded_files")
            log("Files moved successfully to /opt/uploaded_files")
        except Exception as e:
            log(f"Error moving files: {e}")
            # Try copying if move fails
            run_command("sudo cp -r /tmp/uploaded_files/* /opt/uploaded_files/")
            run_command("sudo chown -R ubuntu:ubuntu /opt/uploaded_files")

    # Then copy service files to systemd
    movements = [
        # Service files to systemd
        ("/opt/uploaded_files/scripts/*.service", "/etc/systemd/system/"),
    ]

    for source, dest in movements:
        if "*" in source:
            # Handle glob patterns
            import glob

            for file in glob.glob(source):
                if os.path.exists(file):
                    filename = os.path.basename(file)
                    dest_file = os.path.join(dest, filename)
                    # Use sudo for system directories
                    run_command(f"sudo cp {file} {dest_file}")
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

    # Define services to enable (only bacalhau, sensor is handled by additional_commands.sh)
    services = [
        "bacalhau.service",
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

            # Services will start on reboot after deployment completes


def copy_configuration_files():
    """Copy configuration files to their final locations"""
    # Copy pre-generated Bacalhau config (already has credentials injected)
    bacalhau_config_source = "/opt/uploaded_files/config/bacalhau-config.yaml"
    bacalhau_config_dest = "/bacalhau_node/config.yaml"

    if os.path.exists(bacalhau_config_source):
        Path("/bacalhau_node").mkdir(parents=True, exist_ok=True)
        shutil.copy2(bacalhau_config_source, bacalhau_config_dest)
        os.chown(bacalhau_config_dest, 1000, 1000)  # ubuntu user
        log(f"Installed Bacalhau config at {bacalhau_config_dest}")
    else:
        log("ERROR: Bacalhau config not found in uploaded files")

    # Sensor config is now handled by additional_commands.sh


def run_additional_commands():
    """Run additional commands script if it exists"""
    additional_script = "/opt/uploaded_files/scripts/additional_commands.sh"
    
    if os.path.exists(additional_script):
        log("Running additional commands script...")
        # Make it executable
        run_command(f"chmod +x {additional_script}")
        # Run the script
        result = run_command(additional_script, check=False)
        if result.returncode == 0:
            log("Additional commands completed successfully")
        else:
            log("Warning: Additional commands script returned non-zero exit code")
    else:
        log("No additional commands script found")


def fix_service_dependencies(service_file):
    """Remove dependencies on configure-services.service from service files"""
    try:
        with open(service_file, "r") as f:
            content = f.read()

        # Remove configure-services.service from After= and Requires= lines
        original_content = content
        content = re.sub(r"(After=.*?)\s*configure-services\.service", r"\1", content)
        content = re.sub(
            r"(Requires=.*?)\s*configure-services\.service", r"\1", content
        )
        content = re.sub(r"^Requires=\s*$", "", content, flags=re.MULTILINE)

        if content != original_content:
            with open(service_file, "w") as f:
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
    """Schedule a reboot in 3 seconds"""
    log("Scheduling system reboot in 3 seconds...")
    run_command("shutdown -r +3 'Deployment complete, rebooting system'")


def ensure_uv_installed():
    """Ensure uv is installed and available"""
    log("Checking for uv installation...")

    # Check if uv is already available
    result = run_command("which uv", check=False)
    if result.returncode == 0:
        log(f"uv found at: {result.stdout.strip()}")
        return True

    log("uv not found, installing...")

    # Install uv
    install_cmd = "curl -LsSf https://astral.sh/uv/install.sh | sh"
    result = run_command(install_cmd, check=False)
    if result.returncode != 0:
        log("Failed to install uv via curl")
        return False

    # Move uv to system location
    commands = [
        "mv /root/.cargo/bin/uv /usr/local/bin/uv 2>/dev/null || true",
        "mv ~/.cargo/bin/uv /usr/local/bin/uv 2>/dev/null || true",
        "chmod +x /usr/local/bin/uv",
        "ln -sf /usr/local/bin/uv /usr/bin/uv",
    ]

    for cmd in commands:
        run_command(cmd, check=False)

    # Verify installation
    result = run_command("uv --version", check=False)
    if result.returncode == 0:
        log(f"uv successfully installed: {result.stdout.strip()}")
        return True
    else:
        log("Failed to install uv")
        return False


def main():
    """Main deployment logic"""
    try:
        # Create log file first
        run_command("sudo touch /opt/startup.log")
        run_command("sudo chmod 666 /opt/startup.log")

        log("=== Starting deployment script ===")

        # Ensure uv is installed
        if not ensure_uv_installed():
            log("ERROR: Failed to install uv, but continuing anyway...")

        # Create directories
        create_directories()

        # Move files to correct locations
        move_files()

        # Copy configuration files
        copy_configuration_files()

        # Setup systemd services
        setup_services()

        # Run additional commands (includes sensor setup)
        run_additional_commands()

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
