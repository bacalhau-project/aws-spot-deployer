#!/usr/bin/env python3
"""
Simple startup script that just ensures Docker is ready and logs completion.
All service management is handled by systemd.
"""

import os
import subprocess
import time
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/opt/startup.log", mode="a")
    ]
)

logger = logging.getLogger("startup")

def run_command(command, check=True):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=check
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return e.returncode, e.stdout, e.stderr

def check_docker():
    """Ensure Docker is installed and running."""
    logger.info("Checking Docker installation...")
    
    # Check if docker is installed
    code, stdout, stderr = run_command("docker --version", check=False)
    if code != 0:
        logger.error("Docker is not installed!")
        return False
    
    logger.info(f"Docker version: {stdout.strip()}")
    
    # Check if docker service is running
    code, stdout, stderr = run_command("systemctl is-active docker", check=False)
    if code != 0:
        logger.info("Docker service is not running, starting it...")
        run_command("sudo systemctl start docker")
        time.sleep(5)
    
    # Verify docker is working
    code, stdout, stderr = run_command("docker version", check=False)
    if code != 0:
        logger.error("Docker is not working properly!")
        return False
    
    logger.info("Docker is ready")
    return True

def main():
    """Main function."""
    logger.info("="*60)
    logger.info("Simple startup script starting")
    logger.info(f"Current time: {datetime.now()}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"User: {os.environ.get('USER', 'unknown')}")
    logger.info("="*60)
    
    # Change to ubuntu home directory
    home_dir = "/home/ubuntu"
    if os.path.exists(home_dir):
        os.chdir(home_dir)
        logger.info(f"Changed to directory: {home_dir}")
    
    # Check Docker
    if not check_docker():
        logger.error("Docker check failed!")
        return 1
    
    # Create marker file to indicate startup completed
    marker_file = "/tmp/startup_complete"
    with open(marker_file, "w") as f:
        f.write(f"Startup completed at {datetime.now()}\n")
    
    logger.info("Startup script completed successfully")
    logger.info("Services will be managed by systemd")
    logger.info("="*60)
    
    # No reboot needed - services will start in sequence
    logger.info("Initial setup complete - services will start automatically")
    
    return 0

if __name__ == "__main__":
    exit(main())