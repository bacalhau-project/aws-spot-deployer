#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "requests",
#     "pyyaml",
#     "boto3",
#     "rich",
# ]
# ///

import os
import subprocess
import time
import boto3
import sys
import logging
from rich.console import Console
from rich.logging import RichHandler
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[
        RichHandler(rich_tracebacks=True),
        logging.FileHandler("/opt/startup.log", mode="a")
    ]
)

console = Console()
logger = logging.getLogger("startup")

def check_docker():
    """Check if Docker is installed and running."""
    console.print("Checking Docker installation...", style="bold cyan")
    
    # Check if docker is already installed
    result = run_command(["docker", "--version"])
    if result[0] != 0:
        console.print("Docker not found!", style="bold red")
        raise Exception("Docker should be pre-installed on the instance")
    
    # Ensure docker service is running first
    result = run_command(["sudo", "systemctl", "is-active", "docker"])
    if result[0] != 0:
        console.print("Starting Docker service...", style="yellow")
        run_command(["sudo", "systemctl", "start", "docker"], critical=True)
        time.sleep(2)  # Give Docker time to start
    
    # Check if docker compose plugin is available
    result = run_command(["docker", "compose", "version"])
    if result[0] != 0:
        console.print("Docker Compose plugin not found!", style="bold red")
        console.print("This should have been installed from Docker's official repository", style="red")
        raise Exception("Docker Compose plugin not available")
    
    console.print("Docker is ready", style="bold green")

def get_instance_metadata(metadata_key):
    """Get instance metadata from the EC2 metadata service."""
    try:
        response = subprocess.check_output(['curl', '-s', f'http://169.254.169.254/latest/meta-data/{metadata_key}'])
        return response.decode('utf-8')
    except Exception as e:
        logger.error(f"Error fetching instance metadata for {metadata_key}: {e}")
        console.print(f"Error fetching instance metadata for {metadata_key}: {e}", style="bold red")
        return None

def get_instance_tags():
    """Get instance tags from the EC2 metadata service."""
    instance_id = get_instance_metadata('instance-id')
    region = get_instance_metadata('placement/region')
    if not instance_id or not region:
        return {}

    try:
        # Get IAM role token for instance metadata
        token_response = subprocess.check_output([
            'curl', '-X', 'PUT', '-H', 'X-aws-ec2-metadata-token-ttl-seconds: 21600',
            'http://169.254.169.254/latest/api/token'
        ], timeout=2)
        _ = token_response.decode('utf-8').strip()
        
        # Try to use EC2 credentials from instance profile
        session = boto3.Session(region_name=region)
        ec2 = session.client('ec2')
        response = ec2.describe_tags(Filters=[{'Name': 'resource-id', 'Values': [instance_id]}])
        return {tag['Key']: tag['Value'] for tag in response['Tags']}
    except Exception as e:
        logger.warning(f"Error fetching instance tags: {e}")
        console.print(f"Error fetching instance tags: {e}", style="bold yellow")
        console.print("Continuing without tags...", style="yellow")
        return {}

def run_command(command, critical=False, timeout=300):
    """Run a shell command and print its output."""
    # Add quiet flags for apt commands
    if len(command) >= 2 and command[0] == "sudo" and command[1] == "apt-get":
        if "update" in command:
            command = command[:2] + ["-qq"] + command[2:]
        elif "install" in command and "-qq" not in command:
            command = command[:2] + ["-qq"] + command[2:]
    
    cmd_str = ' '.join(command)
    logger.info(f"Running command: {cmd_str}")
    console.print(f"Running command: {cmd_str}", style="bold cyan")
    
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        output = []
        start_time = time.time()
        
        while True:
            if time.time() - start_time > timeout:
                process.kill()
                raise subprocess.TimeoutExpired(command, timeout)
            
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                print(line, end='')
                logger.info(line.rstrip())
                output.append(line)
        
        process.wait()
        if process.returncode != 0:
            logger.error(f"Command failed with exit code {process.returncode}")
            console.print(f"Command failed with exit code {process.returncode}", style="bold red")
            if critical:
                raise Exception(f"Critical command failed: {cmd_str}")
        return process.returncode, ''.join(output)
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout}s: {cmd_str}")
        console.print(f"Command timed out after {timeout}s", style="bold red")
        if critical:
            raise
        return -1, f"Timeout after {timeout}s"
    except Exception as e:
        logger.error(f"Error running command: {e}")
        console.print(f"Error running command: {e}", style="bold red")
        if critical:
            raise
        return -1, str(e)

def main():
    """Main function to set up and start Bacalhau."""
    # Change to home directory
    home_dir = os.path.expanduser("~")
    os.chdir(home_dir)
    
    logger.info("="*60)
    logger.info("Starting Bacalhau setup script")
    logger.info(f"Current time: {datetime.now()}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info("="*60)
    
    console.print("Starting Bacalhau setup...", style="bold green")
    console.print(f"Current time: {datetime.now()}", style="dim")
    console.print(f"Working directory: {os.getcwd()}", style="dim")

    # Get tags to check for a custom Docker Compose file
    tags = {}
    try:
        tags = get_instance_tags()
    except Exception as e:
        logger.warning(f"Could not get instance tags: {e}")
        console.print("Proceeding without instance tags", style="yellow")
    
    docker_compose_url = tags.get('BacalhauDockerComposeUrl')

    # Define paths
    scripts_dir = "/opt/uploaded_files/scripts"
    docker_compose_path = os.path.join(scripts_dir, "docker-compose.yaml")

    # If a URL is provided in the tags, download the Docker Compose file
    if docker_compose_url:
        console.print(f"Downloading Docker Compose file from: {docker_compose_url}", style="bold blue")
        run_command(['wget', '-O', docker_compose_path, docker_compose_url])
    else:
        console.print("Using default Docker Compose file.", style="bold blue")

    # Ensure Docker is installed and running
    try:
        check_docker()
    except Exception as e:
        logger.error(f"Docker check failed: {e}")
        console.print(f"Docker check failed: {e}", style="bold red")
        console.print("This instance should have Docker pre-installed!", style="bold red")
        sys.exit(1)
    
    # Start Bacalhau using Docker Compose
    if os.path.exists(docker_compose_path):
        console.print("Starting Bacalhau with Docker Compose...", style="bold green")
        logger.info(f"Using docker-compose file: {docker_compose_path}")
        
        # Show docker-compose content for debugging
        console.print("\nDocker Compose configuration:", style="dim")
        run_command(['cat', docker_compose_path])
        
        compose_result = run_command(['docker', 'compose', '--ansi', 'never', '-f', docker_compose_path, 'up', '-d'], critical=True)
        if compose_result[0] == 0:
            console.print("Bacalhau started successfully", style="bold green")
            # Wait for containers to be ready
            console.print("Waiting for containers to initialize...", style="yellow")
            time.sleep(10)
            
            # Show container status
            console.print("\nContainer status:", style="bold blue")
            run_command(['docker', 'compose', '--ansi', 'never', '-f', docker_compose_path, 'ps'])
            
            # Show container logs
            console.print("\nContainer logs:", style="bold blue")
            run_command(['docker', 'compose', '--ansi', 'never', '-f', docker_compose_path, 'logs', '--tail=20'])
        else:
            console.print("Failed to start Bacalhau", style="bold red")
    else:
        console.print(f"docker-compose.yaml not found at {docker_compose_path}", style="bold red")
        console.print("Checking for file in uploaded directories...", style="yellow")
        run_command(['find', '/opt/uploaded_files', '-name', '*.yaml', '-o', '-name', '*.yml'])
        run_command(['find', '/tmp/uploaded_files', '-name', '*.yaml', '-o', '-name', '*.yml'])

    # Setup sensor service
    setup_sensor_service()
    
    # Generate demo node identity
    generate_node_identity()
    
    console.print("\n" + "="*50, style="bold cyan")
    console.print("Bacalhau setup script finished.", style="bold green")
    console.print("="*50 + "\n", style="bold cyan")
    
    # Final status check
    console.print("Final Status Check:", style="bold blue")
    run_command(["sudo", "systemctl", "status", "sensor-log-generator", "--no-pager", "-l"])
    console.print("\nDocker containers:", style="bold blue")
    run_command(["docker", "ps", "-a"])
    
    console.print("\nSensor data is now being generated in demo locations!")
    console.print("Check /opt/sensor/data/sensor_data.db for generated data")


def setup_sensor_service():
    """Setup and start the sensor log generator service."""
    console.print("Setting up sensor log generator service...", style="bold cyan")
    
    try:
        # Create sensor directories
        sensor_dirs = ["/opt/sensor/config", "/opt/sensor/data", "/opt/sensor/logs", "/opt/sensor/exports"]
        for directory in sensor_dirs:
            os.makedirs(directory, exist_ok=True)
            os.system(f"sudo chown -R ubuntu:ubuntu {directory}")
        
        # Copy systemd service file
        service_file = "/etc/systemd/system/sensor-log-generator.service"
        if os.path.exists(service_file):
            run_command(["sudo", "rm", service_file])
        
        # Check both possible locations for uploaded files
        scripts_locations = ["/opt/uploaded_files/scripts", "/tmp/uploaded_files/scripts"]
        config_locations = ["/opt/uploaded_files/config", "/tmp/uploaded_files/config"]
        
        service_src = None
        for loc in scripts_locations:
            if os.path.exists(f"{loc}/sensor-log-generator.service"):
                service_src = f"{loc}/sensor-log-generator.service"
                break
        
        config_src = None
        for loc in config_locations:
            if os.path.exists(f"{loc}/sensor-config.yaml"):
                config_src = f"{loc}/sensor-config.yaml"
                break
        
        if service_src:
            run_command(["sudo", "cp", service_src, service_file])
            run_command(["sudo", "systemctl", "daemon-reload"])
        else:
            console.print("sensor-log-generator.service not found in any location", style="bold red")
            return
        
        # Copy sensor configuration
        if config_src:
            run_command(["sudo", "cp", config_src, "/opt/sensor/config/"])
            run_command(["sudo", "chown", "-R", "ubuntu:ubuntu", "/opt/sensor"])
            run_command(["sudo", "chmod", "644", "/opt/sensor/config/sensor-config.yaml"])
        else:
            console.print("sensor-config.yaml not found in any location", style="bold red")
            return
        
        # Start sensor service
        console.print("Starting sensor log generator service...", style="bold cyan")
        run_command(["sudo", "systemctl", "enable", "sensor-log-generator"])
        run_command(["sudo", "systemctl", "start", "sensor-log-generator"])
        
        # Wait a moment for service to start
        time.sleep(3)
        
        # Check service status
        console.print("Checking sensor service status...", style="bold cyan")
        status_result = run_command(["sudo", "systemctl", "is-active", "sensor-log-generator"])
        if status_result[0] == 0:
            console.print("Sensor service is active", style="bold green")
        else:
            console.print("Sensor service failed to start", style="bold red")
            run_command(["sudo", "journalctl", "-u", "sensor-log-generator", "-n", "50"])
        
    except Exception as e:
        logger.error(f"Error setting up sensor service: {e}")
        console.print(f"Error setting up sensor service: {e}", style="bold red")


def generate_node_identity():
    """Generate demo-friendly node identity for sensor simulation."""
    console.print("Generating demo node identity...", style="bold blue")
    
    try:
        # Run the demo identity generation script
        result = subprocess.run([
            'python3', 
            '/opt/uploaded_files/scripts/generate_demo_identity.py'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            console.print("Demo node identity generated successfully", style="bold green")
            console.print(result.stdout, style="dim")
        else:
            console.print("Failed to generate demo identity", style="bold red")
            console.print(result.stderr, style="bold red")
            
    except Exception as e:
        logger.error(f"Error generating demo identity: {e}")
        console.print(f"Error generating demo identity: {e}", style="bold red")

if __name__ == "__main__":
    try:
        main()
        logger.info("Startup script completed successfully")
        
        # Schedule a reboot to ensure all containers restart properly
        console.print("\n" + "="*50, style="bold cyan")
        console.print("Scheduling system reboot in 10 seconds to ensure all services start properly...", style="bold yellow")
        console.print("="*50 + "\n", style="bold cyan")
        
        logger.info("Scheduling reboot to ensure container restart")
        run_command(["sudo", "shutdown", "-r", "+1", "Startup complete, rebooting to ensure containers restart"])
        
        sys.exit(0)
    except Exception as e:
        logger.error(f"Startup script failed: {e}", exc_info=True)
        console.print(f"\nStartup script failed: {e}", style="bold red")
        sys.exit(1)