#!/usr/bin/env uv run -s
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "boto3",
#     "pyyaml",
#     "rich",
# ]
# ///
"""
AWS Spot Instance Deployer - Single File Version

A simple tool for deploying and managing AWS spot instances with beautiful Rich output.
Focused on simplicity and maintainability over enterprise features.

Usage:
    ./deploy_spot.py setup     # Setup environment
    ./deploy_spot.py create    # Deploy spot instances
    ./deploy_spot.py list      # List running instances
    ./deploy_spot.py destroy   # Terminate instances and cleanup resources
    ./deploy_spot.py --help    # Show help

Features:
    - Enhanced console logging with instance ID and IP address context
    - Log messages show: [i-1234567890abcdef0 @ 54.123.45.67] SUCCESS: Created
    - Makes it easy to identify which instance is producing each log message

Single file with all functionality included.
"""

import base64
import json
import logging
import os
import random
import subprocess
import sys
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional

import boto3
import yaml

try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
        TimeElapsedColumn,
    )
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None

# =============================================================================
# UI CONSTANTS
# =============================================================================


class ColumnWidths:
    """Defines the widths for the Rich status table columns."""

    REGION = 20
    INSTANCE_ID = 22
    STATUS = 35
    TYPE = 12
    PUBLIC_IP = 18
    CREATED = 28  # Increased to fit ISO 8601 time
    PADDING = 7  # for borders and spacing

    @classmethod
    def get_total_width(cls):
        return sum(
            [
                cls.REGION,
                cls.INSTANCE_ID,
                cls.STATUS,
                cls.TYPE,
                cls.PUBLIC_IP,
                cls.CREATED,
                cls.PADDING,
            ]
        )


# =============================================================================
# RICH OUTPUT HELPERS
# =============================================================================


def rich_print(text: str, style: str = None) -> None:
    """Print with Rich styling if available, fallback to regular print."""
    if RICH_AVAILABLE and console:
        console.print(text, style=style)
    else:
        print(text)


def rich_status(text: str) -> None:
    """Print status message with Rich styling."""
    if RICH_AVAILABLE and console:
        console.print(f"[bold blue]INFO: {text}[/bold blue]")
    else:
        print(f"INFO: {text}")


def rich_success(text: str) -> None:
    """Print success message with Rich styling."""
    if RICH_AVAILABLE and console:
        console.print(f"[bold green]SUCCESS: {text}[/bold green]")
    else:
        print(f"SUCCESS: {text}")


def rich_error(text: str) -> None:
    """Print error message with Rich styling."""
    if RICH_AVAILABLE and console:
        console.print(f"[bold red]ERROR: {text}[/bold red]")
    else:
        print(f"ERROR: {text}")


def rich_warning(text: str) -> None:
    """Print warning message with Rich styling."""
    if RICH_AVAILABLE and console:
        console.print(f"[bold yellow]WARN: {text}[/bold yellow]")
    else:
        print(f"WARN: {text}")


# =============================================================================
# CONFIGURATION
# =============================================================================


class SimpleConfig:
    """Enhanced configuration loader with full options support."""

    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = config_file
        self.data = self._load_config()

    def _load_config(self) -> Dict:
        """Load YAML configuration."""
        try:
            with open(self.config_file, "r") as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            print(f"Config file {self.config_file} not found. Run 'setup' first.")
            return {}
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}

    def regions(self) -> List[str]:
        """Get list of regions."""
        return [list(region.keys())[0] for region in self.data.get("regions", [])]

    def instance_count(self) -> int:
        """Get total instance count."""
        return self.data.get("aws", {}).get("total_instances", 3)

    def username(self) -> str:
        """Get SSH username."""
        return self.data.get("aws", {}).get("username", "ubuntu")

    def ssh_key_name(self) -> Optional[str]:
        """Get SSH key name if configured."""
        return self.data.get("aws", {}).get("ssh_key_name")

    def public_ssh_key_path(self) -> Optional[str]:
        """Get public SSH key file path."""
        return self.data.get("aws", {}).get("public_ssh_key_path")

    def private_ssh_key_path(self) -> Optional[str]:
        """Get private SSH key file path."""
        return self.data.get("aws", {}).get("private_ssh_key_path")

    def public_ssh_key_content(self) -> Optional[str]:
        """Get public SSH key content."""
        key_path = self.public_ssh_key_path()
        if key_path and os.path.exists(key_path):
            try:
                with open(key_path, "r") as f:
                    return f.read().strip()
            except Exception as e:
                print(f"Error reading public key: {e}")
        return None

    def files_directory(self) -> str:
        """Get files directory path."""
        return self.data.get("aws", {}).get("files_directory", "files")

    def scripts_directory(self) -> str:
        """Get scripts directory path."""
        return self.data.get("aws", {}).get("scripts_directory", "instance/scripts")

    def cloud_init_template(self) -> str:
        """Get cloud-init template path."""
        return self.data.get("aws", {}).get(
            "cloud_init_template", "instance/cloud-init/init-vm-template.yml"
        )

    def startup_script(self) -> str:
        """Get startup script path."""
        return self.data.get("aws", {}).get(
            "startup_script", "instance/scripts/startup.py"
        )

    def additional_commands_script(self) -> Optional[str]:
        """Get additional commands script path."""
        return self.data.get("aws", {}).get("additional_commands_script")

    def bacalhau_data_dir(self) -> str:
        """Get Bacalhau data directory."""
        return self.data.get("aws", {}).get("bacalhau_data_dir", "/bacalhau_data")

    def bacalhau_node_dir(self) -> str:
        """Get Bacalhau node directory."""
        return self.data.get("aws", {}).get("bacalhau_node_dir", "/bacalhau_node")

    def bacalhau_config_template(self) -> str:
        """Get Bacalhau config template path."""
        return self.data.get("aws", {}).get(
            "bacalhau_config_template", "instance/config/config-template.yaml"
        )

    def docker_compose_template(self) -> str:
        """Get Docker Compose template path."""
        return self.data.get("aws", {}).get(
            "docker_compose_template", "instance/scripts/docker-compose.yaml"
        )

    def spot_price_limit(self) -> Optional[float]:
        """Get spot price limit."""
        return self.data.get("aws", {}).get("spot_price_limit")

    def instance_storage_gb(self) -> int:
        """Get instance storage size in GB."""
        return self.data.get("aws", {}).get("instance_storage_gb", 20)

    def security_groups(self) -> List[str]:
        """Get additional security groups."""
        return self.data.get("aws", {}).get("security_groups", [])

    def iam_instance_profile(self) -> Optional[str]:
        """Get IAM instance profile if configured."""
        return self.data.get("aws", {}).get("iam_instance_profile")

    def vpc_id(self) -> Optional[str]:
        """Get specific VPC ID."""
        return self.data.get("aws", {}).get("vpc_id")

    def subnet_id(self) -> Optional[str]:
        """Get specific subnet ID."""
        return self.data.get("aws", {}).get("subnet_id")

    def associate_public_ip(self) -> bool:
        """Check if instances should have public IP."""
        return self.data.get("aws", {}).get("associate_public_ip", True)

    def tags(self) -> Dict[str, str]:
        """Get additional tags for instances."""
        return self.data.get("aws", {}).get("tags", {})

    def region_config(self, region: str) -> Dict:
        """Get config for specific region."""
        for r in self.data.get("regions", []):
            if region in r:
                return r[region]
        return {"machine_type": "t3.medium", "image": "auto"}


# =============================================================================
# SIMPLE CACHE UTILITIES
# =============================================================================


def cache_file_fresh(filepath: str, max_age_hours: int = 24) -> bool:
    """Check if cache file is fresh."""
    if not os.path.exists(filepath):
        return False
    age_hours = (time.time() - os.path.getmtime(filepath)) / 3600
    return age_hours < max_age_hours


def load_cache(filepath: str) -> Optional[Dict]:
    """Load data from cache file."""
    if cache_file_fresh(filepath):
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def save_cache(filepath: str, data: Dict) -> None:
    """Save data to cache file."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception:
        pass


# =============================================================================
# SIMPLE STATE MANAGEMENT
# =============================================================================


class SimpleStateManager:
    """Simple JSON-based state management - replaces SQLite complexity."""

    def __init__(self, state_file: str = "instances.json"):
        self.state_file = state_file

    def load_instances(self) -> List[Dict]:
        """Load instances from JSON file."""
        try:
            with open(self.state_file, "r") as f:
                data = json.load(f)
                return data.get("instances", [])
        except FileNotFoundError:
            return []
        except Exception as e:
            print(f"Error loading state: {e}")
            return []

    def save_instances(self, instances: List[Dict]) -> None:
        """Save instances to JSON file."""
        try:
            data = {"instances": instances, "last_updated": datetime.now().isoformat()}
            with open(self.state_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving state: {e}")

    def add_instance(self, instance: Dict) -> None:
        """Add instance to state."""
        instances = self.load_instances()
        instances.append(instance)
        self.save_instances(instances)

    def remove_instances_by_region(self, region: str) -> int:
        """Remove instances from specific region."""
        instances = self.load_instances()
        original_count = len(instances)
        instances = [i for i in instances if i.get("region") != region]
        self.save_instances(instances)
        return original_count - len(instances)


# =============================================================================
# AWS UTILITIES
# =============================================================================


def get_latest_ubuntu_ami(region: str, log_function=None) -> Optional[str]:
    """Get latest Ubuntu 22.04 LTS AMI for region."""
    cache_file = f".aws_cache/ami_{region}.json"

    def log_message(msg: str):
        if log_function:
            log_function(msg)
        else:
            print(msg)

    # Try cache first
    cached = load_cache(cache_file)
    if cached and "ami_id" in cached:
        log_message(f"Using cached AMI for {region}: {cached['ami_id']}")
        return cached["ami_id"]

    # Fetch from AWS
    try:
        log_message(f"Fetching AMI for {region}...")
        ec2 = boto3.client("ec2", region_name=region)
        response = ec2.describe_images(
            Owners=["099720109477"],  # Canonical
            Filters=[
                {
                    "Name": "name",
                    "Values": [
                        "ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"
                    ],
                },
                {"Name": "state", "Values": ["available"]},
            ],
            # Remove MaxResults - it seems to cause issues
        )

        log_message(
            f"AMI response for {region}: {len(response.get('Images', []))} images found"
        )

        if response["Images"]:
            # Sort by creation date to get latest
            images = sorted(
                response["Images"], key=lambda x: x["CreationDate"], reverse=True
            )
            ami_id = images[0]["ImageId"]
            log_message(f"Found AMI for {region}: {ami_id}")
            # Cache result
            save_cache(
                cache_file, {"ami_id": ami_id, "timestamp": datetime.now().isoformat()}
            )
            return ami_id
        else:
            log_message(f"No Ubuntu AMIs found for {region}")
    except Exception as e:
        log_message(f"Error getting AMI for {region}: {e}")

    return None


def check_aws_auth() -> bool:
    """Quick AWS authentication check."""
    try:
        sts = boto3.client("sts")
        sts.get_caller_identity()
        return True
    except Exception as e:
        if "token has expired" in str(e).lower():
            rich_error("AWS credentials expired. Run: aws sso login")
        else:
            rich_error(f"AWS authentication failed: {e}")
        return False


# =============================================================================
# CONSOLE LOGGER FOR THREAD OUTPUT
# =============================================================================


class ConsoleLogger(logging.Handler):
    """Custom logging handler that adds instance context to console output."""
    
    def __init__(self, console_obj=None, instance_ip_map=None):
        super().__init__()
        self.console = console_obj or console
        self.instance_ip_map = instance_ip_map or {}
        self.setLevel(logging.INFO)
        
    def emit(self, record):
        try:
            msg = self.format(record)
            
            # Check if the message already contains instance ID and IP (like "[i-12345 @ 1.2.3.4] SUCCESS: Created")
            import re
            instance_pattern = re.match(r'^\[([i-][a-z0-9]+)\s*@\s*([\d.]+)\]\s*(.*)', msg)
            
            if instance_pattern:
                # Message already has instance ID and IP, use as-is
                pass  # The message is already formatted correctly
            else:
                # Extract instance key from thread name if available
                thread_name = record.threadName
                instance_key = None
                instance_ip = None
                
                # Thread names are like "Setup-i-1234567890abcdef0" or "Region-us-west-2"
                if thread_name.startswith("Setup-"):
                    instance_key = thread_name.replace("Setup-", "")
                    # Look up IP address from our map
                    instance_ip = self.instance_ip_map.get(instance_key, "")
                elif "-" in thread_name and thread_name.split("-")[0] == "Region":
                    # For region threads, try to extract from the message
                    if "[" in msg and "]" in msg:
                        # Message already has instance key
                        # Try to extract it to look up IP
                        match = re.search(r'\[([^\]]+)\]', msg)
                        if match:
                            potential_key = match.group(1)
                            if potential_key in self.instance_ip_map:
                                instance_key = potential_key
                                instance_ip = self.instance_ip_map.get(instance_key, "")
                    else:
                        # Add region context
                        region = thread_name.replace("Region-", "")
                        msg = f"[{region}] {msg}"
                
                # Build the prefix with instance key and IP
                prefix = ""
                if instance_key:
                    if instance_ip:
                        prefix = f"[{instance_key} @ {instance_ip}]"
                    else:
                        prefix = f"[{instance_key}]"
                    
                    # Only add prefix if it's not already in the message
                    if not msg.startswith(prefix) and not msg.startswith(f"[{instance_key}"):
                        msg = f"{prefix} {msg}"
            
            # Only print SUCCESS and ERROR messages to console
            if "SUCCESS:" in msg or "ERROR:" in msg:
                # Print with appropriate styling
                if "SUCCESS:" in msg:
                    if self.console and RICH_AVAILABLE:
                        self.console.print(f"[bold green]{msg}[/bold green]")
                    else:
                        print(msg)
                elif "ERROR:" in msg:
                    if self.console and RICH_AVAILABLE:
                        self.console.print(f"[bold red]{msg}[/bold red]")
                    else:
                        print(msg)
                        
        except Exception:
            self.handleError(record)


# =============================================================================
# REAL-TIME PROGRESS TRACKING
# =============================================================================


class ProgressTracker:
    """Enhanced progress tracking with Rich progress bars and detailed status updates."""

    def __init__(self):
        self.console = console if RICH_AVAILABLE else None
        self.progress_bars = {}
        self.overall_progress = None
        self.tasks = {}

    def create_overall_progress(self, total_instances: int):
        """Create overall progress bar for all instances."""
        if not RICH_AVAILABLE:
            return

        self.overall_progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(complete_style="green", finished_style="green"),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=self.console,
            transient=True,
        )

        overall_task = self.overall_progress.add_task(
            f"Deploying {total_instances} instances",
            total=total_instances * 6,  # 6 phases per instance
        )

        return overall_task

    def create_instance_progress(self, instance_key: str, description: str):
        """Create individual progress bar for a specific instance."""
        if not RICH_AVAILABLE:
            return

        if instance_key not in self.progress_bars:
            self.progress_bars[instance_key] = Progress(
                SpinnerColumn(),
                TextColumn("[bold cyan]{task.description}"),
                BarColumn(complete_style="blue", finished_style="green"),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=self.console,
                transient=True,
            )

        task = self.progress_bars[instance_key].add_task(description, total=100)
        self.tasks[instance_key] = task
        return task

    def update_instance_progress(
        self, instance_key: str, phase: str, progress: int, status: str = ""
    ):
        """Update progress for a specific instance phase."""
        if not RICH_AVAILABLE or instance_key not in self.tasks:
            return

        self.progress_bars[instance_key].update(
            self.tasks[instance_key],
            description=f"{phase}: {status}",
            completed=progress,
        )

    def complete_instance_progress(self, instance_key: str, success: bool = True):
        """Mark instance progress as complete."""
        if not RICH_AVAILABLE or instance_key not in self.tasks:
            return

        status = "✅ Complete" if success else "❌ Failed"
        self.progress_bars[instance_key].update(
            self.tasks[instance_key], description=status, completed=100
        )


# =============================================================================
# FILE AND SCRIPT HANDLING
# =============================================================================


def generate_minimal_cloud_init(config: SimpleConfig) -> str:
    """Generate minimal cloud-init script for basic setup only."""
    # Get public SSH key content
    public_key = config.public_ssh_key_content()
    if not public_key:
        rich_warning("No public SSH key found - SSH access may not work")
        public_key = ""

    # Create minimal cloud-init script
    cloud_init_script = f"""#cloud-config

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
  - curl
  - wget
  - unzip
  - git
  - python3
  - python3-pip
  - ca-certificates
  - gnupg
  - lsb-release

runcmd:
  - echo "Package updates starting" > /tmp/cloud-init-status
  - echo "[$(date)] Cloud-init starting" >> /var/log/startup-progress.log
  
  # Create directories for uploaded files immediately
  - mkdir -p /opt/uploaded_files/scripts /opt/uploaded_files/config
  - mkdir -p /tmp/uploaded_files/scripts /tmp/uploaded_files/config
  - mkdir -p /tmp/exs  # Temporary location for service files
  - chown -R {config.username()}:{config.username()} /opt/uploaded_files
  - chown -R {config.username()}:{config.username()} /tmp/uploaded_files
  - chown -R {config.username()}:{config.username()} /tmp/exs
  - chmod -R 755 /opt/uploaded_files /tmp/uploaded_files /tmp/exs
  - echo "Upload directories created" > /tmp/cloud-init-status
  
  # Create startup log with proper permissions
  - touch /opt/startup.log
  - chown {config.username()}:{config.username()} /opt/startup.log
  - chmod 666 /opt/startup.log
  
  # Install Docker from official repository
  - echo "Installing Docker" > /tmp/cloud-init-status
  - mkdir -p /etc/apt/keyrings
  - curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  - echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
  - apt-get update
  - apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  - systemctl enable docker
  - systemctl start docker
  - usermod -aG docker {config.username()}
  - docker --version
  - docker compose version
  
  - echo "SSH key setup" > /tmp/cloud-init-status
  # Ensure SSH directory is properly set up
  - mkdir -p /home/{config.username()}/.ssh
  - echo "{public_key}" > /home/{config.username()}/.ssh/authorized_keys
  - chown -R {config.username()}:{config.username()} /home/{config.username()}/.ssh
  - chmod 700 /home/{config.username()}/.ssh
  - chmod 600 /home/{config.username()}/.ssh/authorized_keys
  
  - echo "Installing uv" > /tmp/cloud-init-status
  # Install uv for Python scripts
  - curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="/usr/local/bin" sh
  - chmod 755 /usr/local/bin/uv
  
  - echo "Finalizing setup" > /tmp/cloud-init-status
  
  # Wait for Docker to be fully ready
  - systemctl is-active --quiet docker || systemctl restart docker
  - sleep 5
  - docker version
  - docker compose version || echo "Docker Compose will be checked by startup script"
  
  # Signal that instance is ready
  - echo "Cloud-init finalizing" > /tmp/cloud-init-status
  - echo "[$(date)] All configurations complete" >> /var/log/startup-progress.log
  - echo "Instance setup complete" > /tmp/setup_complete
  - chown {config.username()}:{config.username()} /tmp/setup_complete
  - echo "Ready for connections" > /tmp/cloud-init-status
  
  # Create a marker file to signal cloud-init completion
  - echo "[$(date)] Cloud-init base setup complete" > /tmp/cloud-init-complete
  - echo "Base setup complete" > /tmp/cloud-init-status
  
  # Ensure Docker is fully installed and running
  - |
    echo "Verifying Docker installation..." >> /var/log/startup-progress.log
    for i in {{1..30}}; do
      if systemctl is-active --quiet docker && docker --version && docker compose version; then
        echo "Docker verified as working" >> /var/log/startup-progress.log
        break
      else
        echo "Waiting for Docker to be ready... (attempt $i/30)" >> /var/log/startup-progress.log
        sleep 2
      fi
    done
  
  # Signal completion
  - echo "[$(date)] Cloud-init initial setup complete" >> /var/log/startup-progress.log
  - echo "[$(date)] Waiting for file upload and service configuration" >> /opt/startup.log
  
# Note: We do NOT reboot here. Services will start naturally after files are uploaded.
"""

    return cloud_init_script


def wait_for_instance_ready(
    hostname: str,
    username: str,
    private_key_path: str,
    timeout: int = 300,
    instance_key: str = None,
    update_status_func=None,
    progress_callback=None,
) -> bool:
    """Wait for SSH to be ready and for cloud-init to finish with detailed progress tracking."""
    start_time = time.time()
    ssh_ready = False
    last_log_time = 0

    def update_progress(phase, progress, status=""):
        if progress_callback and instance_key:
            progress_callback(instance_key, phase, progress, status)
        if update_status_func and instance_key:
            update_status_func(instance_key, f"{phase}: {status}")

    update_progress("SSH: Connection", 0, "Starting SSH connection check...")

    while time.time() - start_time < timeout:
        elapsed = int(time.time() - start_time)

        # Phase 1: Wait for SSH
        if not ssh_ready:
            update_progress(
                "SSH: Connection", 10, f"Attempting SSH connection... ({elapsed}s)"
            )
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
                    timeout=5,
                )
                if result.returncode == 0:
                    ssh_ready = True
                    update_progress(
                        "SSH: Connection", 100, "SSH connection established"
                    )
                    time.sleep(2)  # Brief pause before cloud-init check
                    continue
                else:
                    update_progress(
                        "SSH: Connection",
                        20 + (elapsed * 2),
                        f"SSH not ready... ({elapsed}s)",
                    )
            except (subprocess.TimeoutExpired, Exception):
                update_progress(
                    "SSH: Connection",
                    20 + (elapsed * 2),
                    f"SSH connection failed... ({elapsed}s)",
                )

        # Phase 2: SSH is up, check for cloud-init progress
        if ssh_ready:
            # Occasionally stream live logs for better UX
            current_time = time.time()
            if current_time - last_log_time > 8:  # Every 8 seconds
                last_log_time = current_time
                try:
                    # Get latest meaningful log line
                    log_cmd = 'tail -5 /var/log/cloud-init-output.log 2>/dev/null | grep -E "(Setting up|Installing|Running|Starting|Configuring)" | tail -1'
                    log_result = subprocess.run(
                        [
                            "ssh",
                            "-i",
                            private_key_path,
                            "-o",
                            "StrictHostKeyChecking=no",
                            "-o",
                            "UserKnownHostsFile=/dev/null",
                            "-o",
                            "ConnectTimeout=2",
                            f"{username}@{hostname}",
                            log_cmd,
                        ],
                        capture_output=True,
                        text=True,
                        timeout=3,
                    )
                    if log_result.returncode == 0 and log_result.stdout.strip():
                        log_line = log_result.stdout.strip()[:60]  # Truncate
                        update_progress("Cloud-Init", 0, f"📦 {log_line}")
                except Exception:
                    pass

            update_progress("Cloud-Init", 0, "Checking cloud-init status...")
            try:
                # Enhanced status checking with multiple sources
                check_commands = [
                    'test -f /tmp/setup_complete && echo "SETUP_COMPLETE"',
                    "cat /tmp/cloud-init-status 2>/dev/null",
                    'cloud-init status 2>/dev/null | grep -o "status:.*" | cut -d: -f2',
                    "systemctl is-active docker 2>/dev/null",
                    "tail -1 /var/log/startup-progress.log 2>/dev/null",
                ]

                combined_command = ' && echo "|||" && '.join(check_commands)
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
                        f'bash -c "{combined_command}"',
                    ],
                    capture_output=True,
                    text=True,
                    timeout=6,
                )

                if result.returncode == 0:
                    outputs = result.stdout.strip().split("|||")

                    # Check if setup is complete
                    if len(outputs) > 0 and "SETUP_COMPLETE" in outputs[0]:
                        update_progress("Cloud-Init", 100, "Cloud-init complete")
                        update_progress(
                            "Instance Ready", 100, "Instance is fully ready ✅"
                        )
                        return True

                    # Parse status from different sources
                    status_msg = "Initializing..."
                    progress = 20

                    if len(outputs) > 1 and outputs[1]:
                        cloud_status = outputs[1].strip()
                        if "Docker setup" in cloud_status:
                            status_msg = "Installing Docker..."
                            progress = 40
                        elif "SSH key setup" in cloud_status:
                            status_msg = "Configuring SSH keys..."
                            progress = 35
                        elif "Installing uv" in cloud_status:
                            status_msg = "Installing package manager..."
                            progress = 50
                        elif "Package updates" in cloud_status:
                            status_msg = "Updating packages..."
                            progress = 30
                        elif "Cloud-init finalizing" in cloud_status:
                            status_msg = "Finalizing setup..."
                            progress = 90
                        elif "Ready for connections" in cloud_status:
                            status_msg = "Almost ready..."
                            progress = 95
                        else:
                            status_msg = cloud_status[:50]
                            progress = 60

                    # Check cloud-init official status
                    if len(outputs) > 2 and outputs[2]:
                        ci_status = outputs[2].strip()
                        if "done" in ci_status:
                            progress = max(progress, 85)
                            status_msg = "Cloud-init finishing up..."
                        elif "running" in ci_status:
                            progress = max(progress, 25)

                    # Check Docker status
                    if len(outputs) > 3 and outputs[3] == "active":
                        progress = max(progress, 70)
                        if progress == 70:
                            status_msg = "Docker is ready"

                    # Check startup progress log
                    if len(outputs) > 4 and outputs[4]:
                        startup_log = outputs[4].strip()
                        if "Docker installed" in startup_log:
                            progress = max(progress, 45)
                        elif "SSH keys configured" in startup_log:
                            progress = max(progress, 38)
                        elif "UV package manager installed" in startup_log:
                            progress = max(progress, 55)
                        elif "All configurations complete" in startup_log:
                            progress = max(progress, 92)

                    # Add elapsed time to status
                    if elapsed > 30:
                        status_msg = f"{status_msg} ({elapsed}s)"

                    update_progress("Cloud-Init", progress, status_msg)
                else:
                    update_progress("Cloud-Init", 15, "Waiting for cloud-init...")

            except (subprocess.TimeoutExpired, Exception):
                update_progress("Cloud-Init", 10, "Checking cloud-init status...")

        time.sleep(5)

    update_progress("Timeout", 0, f"Timeout after {timeout}s")
    if update_status_func and instance_key:
        update_status_func(
            instance_key,
            "ERROR: Timeout waiting for instance to be ready.",
            is_final=True,
        )
    return False


def ensure_remote_directories(
    hostname: str,
    username: str,
    private_key_path: str,
    logger=None,
    retry_count: int = 3,
) -> bool:
    """Ensure remote directories exist for file uploads with retry logic."""

    def log_info(message):
        if logger:
            logger.info(message)

    def log_error(message):
        if logger:
            logger.error(message)

    # Define the directories we need
    directories = [
        "/opt/uploaded_files",
        "/opt/uploaded_files/scripts",
        "/opt/uploaded_files/config",
        "/tmp/uploaded_files",
        "/tmp/uploaded_files/scripts",
        "/tmp/uploaded_files/config",
        "/tmp/exs",  # Temporary location for service files
    ]

    for attempt in range(retry_count):
        try:
            log_info(
                f"Directory creation attempt {attempt + 1}/{retry_count} on {hostname}"
            )

            # Build a robust command that handles various scenarios
            commands = []

            # First, try to create parent directories with sudo
            commands.append(
                "sudo mkdir -p /opt/uploaded_files /tmp/uploaded_files 2>/dev/null || true"
            )

            # Set ownership (might fail if no sudo, that's ok)
            commands.append(
                f"sudo chown -R {username}:{username} /opt/uploaded_files /tmp/uploaded_files 2>/dev/null || true"
            )

            # Create all subdirectories (as user, should always work for /tmp at least)
            for dir in directories:
                commands.append(f"mkdir -p {dir} 2>/dev/null || true")

            # Set permissions where we can
            commands.append("chmod -R 755 /opt/uploaded_files 2>/dev/null || true")
            commands.append("chmod -R 755 /tmp/uploaded_files 2>/dev/null || true")

            # Verify at least /tmp directories exist
            commands.append(
                "test -d /tmp/uploaded_files/scripts && test -d /tmp/uploaded_files/config && echo 'DIRS_OK' || echo 'DIRS_FAILED'"
            )

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
                    "-o",
                    "ConnectTimeout=10",
                    f"{username}@{hostname}",
                    full_command,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Check if at least the basic directories were created
            if "DIRS_OK" in result.stdout:
                log_info(f"Successfully created/verified directories on {hostname}")
                return True
            elif attempt < retry_count - 1:
                log_info(
                    f"Directory creation attempt {attempt + 1} failed, retrying..."
                )
                time.sleep(2)  # Brief pause before retry
            else:
                log_error(f"Failed to create directories after {retry_count} attempts")
                log_error(f"stdout: {result.stdout}")
                log_error(f"stderr: {result.stderr}")

        except Exception as e:
            log_error(f"Exception during directory creation attempt {attempt + 1}: {e}")
            if attempt < retry_count - 1:
                time.sleep(2)

    return False


def upload_files_to_instance(
    hostname: str,
    username: str,
    private_key_path: str,
    config: SimpleConfig,
    logger=None,
    progress_callback=None,
    instance_key=None,
) -> bool:
    """Upload files and scripts to the instance with progress tracking."""

    def log_error(message):
        if logger:
            logger.error(message)
        # Don't print to console in hands-off mode

    def update_progress(phase, progress, status=""):
        if progress_callback and instance_key:
            progress_callback(instance_key, phase, progress, status)
    
    def update_status(status):
        """Update status in the main table."""
        if hasattr(upload_files_to_instance, 'update_status_func') and instance_key:
            upload_files_to_instance.update_status_func(instance_key, status)

    try:
        # Upload files directory if it exists and is not empty
        files_dir = config.files_directory()
        if logger:
            logger.info(
                f"Files directory: {files_dir}, exists: {os.path.exists(files_dir)}"
            )

        if os.path.exists(files_dir) and os.listdir(files_dir):
            update_progress("SCP: Files Upload", 25, "Starting files upload...")

            # Count total files for progress calculation
            total_files = len(
                [
                    f
                    for f in os.listdir(files_dir)
                    if os.path.isfile(os.path.join(files_dir, f))
                ]
            )

            result = subprocess.run(
                [
                    "scp",
                    "-i",
                    private_key_path,
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "UserKnownHostsFile=/dev/null",
                    "-o",
                    "ConnectTimeout=10",
                    "-r",
                    f"{files_dir}/.",
                    f"{username}@{hostname}:/opt/uploaded_files/",
                ],
                capture_output=True,
                text=True,
                timeout=120,  # Increased timeout for larger uploads
            )
            if result.returncode != 0:
                log_error(f"Failed to upload files to {hostname}: {result.stderr}")
                return False

            update_progress("SCP: Files Upload", 50, f"Uploaded {total_files} files")

        # Upload scripts directory if it exists and is not empty
        scripts_dir = config.scripts_directory()
        if os.path.exists(scripts_dir) and os.listdir(scripts_dir):
            update_progress("SCP: Scripts Upload", 55, "Starting scripts upload...")
            
            # First, upload service files to /tmp/exs
            service_files = [
                "bacalhau-startup.service",
                "setup-config.service", 
                "bacalhau.service",
                "sensor-generator.service"
            ]
            
            # Upload service files to /tmp/exs
            update_status("UPLOAD: Service files to /tmp/exs...")
            for service_file in service_files:
                service_path = os.path.join(scripts_dir, service_file)
                if os.path.exists(service_path):
                    result = subprocess.run(
                        [
                            "scp",
                            "-i",
                            private_key_path,
                            "-o",
                            "StrictHostKeyChecking=no",
                            "-o",
                            "UserKnownHostsFile=/dev/null",
                            "-o",
                            "ConnectTimeout=10",
                            service_path,
                            f"{username}@{hostname}:/tmp/exs/",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    if result.returncode != 0:
                        log_error(f"Failed to upload {service_file} to /tmp/exs: {result.stderr}")
                        return False
            
            update_progress("SCP: Service Files", 60, "Service files uploaded to /tmp/exs")
            
            # Upload all scripts to /tmp/exs (including non-service files)
            update_status("UPLOAD: All scripts to /tmp/exs...")
            result = subprocess.run(
                [
                    "scp",
                    "-i",
                    private_key_path,
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "UserKnownHostsFile=/dev/null",
                    "-o",
                    "ConnectTimeout=10",
                    "-r",
                    f"{scripts_dir}/.",
                    f"{username}@{hostname}:/tmp/exs/",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                log_error(f"Failed to upload scripts to /tmp/exs: {result.stderr}")
                return False
                
            update_progress("SCP: Scripts Upload", 70, "All scripts uploaded to /tmp/exs")

            # Also copy to /tmp for backward compatibility
            subprocess.run(
                [
                    "scp",
                    "-i",
                    private_key_path,
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "UserKnownHostsFile=/dev/null",
                    "-o",
                    "ConnectTimeout=10",
                    "-r",
                    f"{scripts_dir}/.",
                    f"{username}@{hostname}:/tmp/uploaded_files/scripts/",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            update_progress(
                "SCP: Scripts Upload", 80, "Scripts copied to both locations"
            )

        # Upload config directory if it exists
        config_dir = os.path.join(os.path.dirname(scripts_dir), "config")
        if os.path.exists(config_dir) and os.listdir(config_dir):
            update_progress("SCP: Config Upload", 85, "Uploading config files...")

            result = subprocess.run(
                [
                    "scp",
                    "-i",
                    private_key_path,
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "UserKnownHostsFile=/dev/null",
                    "-o",
                    "ConnectTimeout=10",
                    "-r",
                    f"{config_dir}/.",
                    f"{username}@{hostname}:/opt/uploaded_files/config/",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            # Also copy to /tmp for backward compatibility
            subprocess.run(
                [
                    "scp",
                    "-i",
                    private_key_path,
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "UserKnownHostsFile=/dev/null",
                    "-o",
                    "ConnectTimeout=10",
                    "-r",
                    f"{config_dir}/.",
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


def wait_for_ssh_only(
    hostname: str, username: str, private_key_path: str, timeout: int = 120
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


def enable_startup_service(
    hostname: str, username: str, private_key_path: str, logger=None
) -> bool:
    """Execute the deployment script to configure services."""
    try:
        # First, upload the deploy_services.py script
        deploy_script_path = os.path.join(
            os.path.dirname(__file__), "instance/scripts/deploy_services.py"
        )
        
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
            timeout=120,  # Increased timeout for configure-services to run
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
        return True  # Don't fail on timeout, services may still be configuring
    except Exception as e:
        if logger:
            logger.error(f"Error configuring services: {e}")
        return False


def verify_cloud_init_running(
    hostname: str, username: str, private_key_path: str, logger=None
) -> bool:
    """Quick check that cloud-init is running - no waiting."""
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
                "cloud-init status | grep -E 'status:|running' || ps aux | grep cloud-init | grep -v grep",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if logger:
            logger.info(f"Cloud-init check: {result.stdout}")

        return "running" in result.stdout.lower() or "cloud-init" in result.stdout

    except Exception as e:
        if logger:
            logger.warning(f"Could not verify cloud-init: {e}")
        return False


def setup_reboot_service(
    hostname: str, username: str, private_key_path: str, logger=None
) -> bool:
    """Configure the one-shot startup service and reboot the instance."""
    try:
        # Define the sequence of commands to set up the service and reboot
        commands = [
            "sudo cp /opt/uploaded_files/scripts/bacalhau-startup.service /etc/systemd/system/",
            "sudo systemctl daemon-reload",
            "sudo systemctl enable bacalhau-startup.service",
            "sudo systemctl status bacalhau-startup.service || true",  # Check status
            "echo 'Service enabled, initiating reboot...'",
            "sudo shutdown -r now",  # Use shutdown instead of reboot for better compatibility
        ]

        full_command = " && ".join(commands)

        # Execute the commands via SSH
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
            timeout=60,
        )

        # Log the command output for debugging
        if logger:
            logger.info(f"Setup reboot stdout: {result.stdout}")
            logger.info(f"Setup reboot stderr: {result.stderr}")
            logger.info(f"Setup reboot return code: {result.returncode}")

        # The reboot command means a successful exit code might not be returned.
        # SSH typically returns 255 when connection is closed by remote
        if result.returncode == 0:
            if logger:
                logger.info("Reboot command completed successfully")
            return True
        elif result.returncode == 255:
            # This is expected when SSH connection is closed by reboot
            if logger:
                logger.info("SSH connection closed by reboot (expected)")
            return True
        else:
            stderr_lower = result.stderr.lower()
            stdout_lower = result.stdout.lower()
            # Check for patterns indicating successful reboot initiation
            reboot_patterns = [
                "connection to",
                "closed by remote host",
                "connection reset",
                "broken pipe",
                "connection closed",
                "system is going down",
                "broadcast message",
                "the system will reboot",
            ]
            if any(
                pattern in stderr_lower or pattern in stdout_lower
                for pattern in reboot_patterns
            ):
                if logger:
                    logger.info("Reboot initiated successfully (connection disrupted)")
                return True
            else:
                error_message = f"Failed to set up reboot service - stdout: {result.stdout}, stderr: {result.stderr}, code: {result.returncode}"
                if logger:
                    logger.error(error_message)
                rich_error(error_message)
                return False

    except subprocess.TimeoutExpired:
        # A timeout is expected as the machine reboots
        return True
    except Exception as e:
        # Other exceptions might be expected if the connection is severed by the reboot
        if "connection closed" in str(e).lower():
            return True

        error_message = f"Error setting up reboot service: {e}"
        if logger:
            logger.error(error_message)
        rich_error(error_message)
        return False


# =============================================================================
# CORE SPOT INSTANCE MANAGEMENT
# =============================================================================


def create_simple_security_group(ec2, vpc_id: str) -> str:
    """Create basic security group."""
    try:
        # Check for existing security group
        response = ec2.describe_security_groups(
            Filters=[
                {"Name": "vpc-id", "Values": [vpc_id]},
                {"Name": "group-name", "Values": ["spot-deployer-sg"]},
            ]
        )

        if response["SecurityGroups"]:
            return response["SecurityGroups"][0]["GroupId"]

        # Create new security group
        response = ec2.create_security_group(
            GroupName="spot-deployer-sg",
            Description="Simple security group for spot instances",
            VpcId=vpc_id,
        )
        sg_id = response["GroupId"]

        # Add basic rules
        ec2.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[
                {
                    "IpProtocol": "tcp",
                    "FromPort": 22,
                    "ToPort": 22,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                },
                {
                    "IpProtocol": "tcp",
                    "FromPort": 4222,
                    "ToPort": 4222,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                },
            ],
        )

        return sg_id
    except Exception as e:
        print(f"Error creating security group: {e}")
        raise


def create_instances_in_region(
    config: SimpleConfig, region: str, count: int, progress=None, task=None
) -> List[Dict]:
    """Create spot instances in a specific region."""
    if count <= 0:
        return []

    def update_progress(message: str):
        """Update progress bar if available, otherwise use rich_status."""
        if progress and task is not None:
            progress.update(task, description=message)
            time.sleep(0.2)  # Brief pause to show progress
        else:
            rich_status(message)

    update_progress(f"🔍 Looking for VPC in {region}...")

    try:
        ec2 = boto3.client("ec2", region_name=region)

        # Get default VPC
        vpcs = ec2.describe_vpcs(Filters=[{"Name": "is-default", "Values": ["true"]}])
        if not vpcs["Vpcs"]:
            update_progress(f"🔍 No default VPC in {region}, checking all VPCs...")
            # Try any VPC if no default exists
            all_vpcs = ec2.describe_vpcs()
            if all_vpcs["Vpcs"]:
                vpc_id = all_vpcs["Vpcs"][0]["VpcId"]
                update_progress(f"🏗️  Using VPC {vpc_id} in {region}")
            else:
                rich_warning(f"No VPCs found in {region}, skipping")
                return []
        else:
            vpc_id = vpcs["Vpcs"][0]["VpcId"]
            update_progress(f"🏗️  Using default VPC {vpc_id} in {region}")

        # Get default subnet
        update_progress(f"🔍 Looking for subnet in VPC {vpc_id}...")
        subnets = ec2.describe_subnets(
            Filters=[
                {"Name": "vpc-id", "Values": [vpc_id]},
                {"Name": "default-for-az", "Values": ["true"]},
            ]
        )
        if not subnets["Subnets"]:
            update_progress(f"🔍 No default subnet in {region}, trying any subnet...")
            # Try any subnet in the VPC
            all_subnets = ec2.describe_subnets(
                Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
            )
            if all_subnets["Subnets"]:
                subnet_id = all_subnets["Subnets"][0]["SubnetId"]
                update_progress(f"🌐 Using subnet {subnet_id} in {region}")
            else:
                rich_warning(f"No subnets found in VPC {vpc_id}, skipping")
                return []
        else:
            subnet_id = subnets["Subnets"][0]["SubnetId"]
            update_progress(f"🌐 Using default subnet {subnet_id} in {region}")

        # Create security group
        update_progress(f"🔒 Creating security group in {region}...")
        sg_id = create_simple_security_group(ec2, vpc_id)

        # Get AMI
        update_progress(f"📀 Getting AMI for {region}...")
        ami_id = get_latest_ubuntu_ami(region)
        if not ami_id:
            rich_warning(f"No AMI found for {region}, skipping")
            return []

        # Get instance type
        region_config = config.region_config(region)
        instance_type = region_config.get("machine_type", "t3.medium")

        # Create user data script
        user_data = f"""#!/bin/bash
apt-get update
apt-get install -y docker.io
systemctl enable docker
systemctl start docker
usermod -aG docker {config.username()}
"""

        # Create spot instance request
        update_progress(f"🚀 Requesting spot instances in {region}...")
        spot_request = {
            "ImageId": ami_id,
            "InstanceType": instance_type,
            "SecurityGroupIds": [sg_id],
            "SubnetId": subnet_id,
            "UserData": base64.b64encode(user_data.encode()).decode(),
        }

        # Add SSH key if configured
        ssh_key = config.ssh_key_name()
        if ssh_key:
            spot_request["KeyName"] = ssh_key

        # Request spot instances
        response = ec2.request_spot_instances(
            InstanceCount=count, LaunchSpecification=spot_request, Type="one-time"
        )

        spot_request_ids = [
            req["SpotInstanceRequestId"] for req in response["SpotInstanceRequests"]
        ]
        update_progress(f"⏳ Waiting for spot instances to launch in {region}...")

        # Wait for fulfillment (simplified - max 5 minutes)
        instances = []
        for attempt in range(30):  # 30 * 10s = 5 minutes max
            try:
                spot_response = ec2.describe_spot_instance_requests(
                    SpotInstanceRequestIds=spot_request_ids
                )

                active_requests = [
                    req
                    for req in spot_response["SpotInstanceRequests"]
                    if req["State"] == "active" and "InstanceId" in req
                ]

                if len(active_requests) == count:
                    update_progress(f"🏷️  Tagging instances in {region}...")
                    # Get instance details
                    instance_ids = [req["InstanceId"] for req in active_requests]
                    instance_response = ec2.describe_instances(InstanceIds=instance_ids)

                    for reservation in instance_response["Reservations"]:
                        for instance in reservation["Instances"]:
                            instances.append(
                                {
                                    "id": instance["InstanceId"],
                                    "region": region,
                                    "type": instance["InstanceType"],
                                    "state": instance["State"]["Name"],
                                    "public_ip": instance.get("PublicIpAddress", ""),
                                    "private_ip": instance.get("PrivateIpAddress", ""),
                                    "created": datetime.now().isoformat(),
                                }
                            )

                    # Tag instances
                    if instance_ids:
                        ec2.create_tags(
                            Resources=instance_ids,
                            Tags=[
                                {"Key": "ManagedBy", "Value": "SpotDeployer"},
                                {"Key": "Name", "Value": f"SpotInstance-{region}"},
                            ],
                        )

                    break

                # Check for failed requests
                failed = [
                    req
                    for req in spot_response["SpotInstanceRequests"]
                    if req["State"] in ["failed", "cancelled"]
                ]
                if failed:
                    rich_error(f"Some spot requests failed in {region}")
                    break

                # Update progress with wait time
                update_progress(
                    f"⏳ Waiting for spot instances to launch in {region}... (attempt {attempt + 1}/30)"
                )
                time.sleep(10)

            except Exception as e:
                rich_error(f"Error checking spot requests: {e}")
                break

        if not instances:
            rich_warning(f"No instances created in {region} (timeout or failure)")

        return instances

    except Exception as e:
        rich_error(f"Error creating instances in {region}: {e}")
        return []


def create_instances_in_region_with_table(
    config: SimpleConfig,
    region: str,
    count: int,
    creation_status: Dict,
    lock: threading.Lock,
    logger,
    update_status_func,
) -> List[Dict]:
    """Create spot instances in a specific region with live table updates."""
    if count <= 0:
        return []

    instance_keys = [f"{region}-{i + 1}" for i in range(count)]

    def log_message(msg: str):
        """Thread-safe logging to file."""
        logger.info(msg)

    for key in instance_keys:
        update_status_func(key, "Finding VPC")

    try:
        ec2 = boto3.client("ec2", region_name=region)

        log_message(f"[{region}] Looking for VPC...")
        vpcs = ec2.describe_vpcs(Filters=[{"Name": "is-default", "Values": ["true"]}])
        if not vpcs["Vpcs"]:
            for key in instance_keys:
                update_status_func(key, "Finding any VPC")
            log_message(f"[{region}] No default VPC, checking all VPCs...")
            all_vpcs = ec2.describe_vpcs()
            if all_vpcs["Vpcs"]:
                vpc_id = all_vpcs["Vpcs"][0]["VpcId"]
                for key in instance_keys:
                    update_status_func(key, "Using VPC")
                log_message(f"[{region}] Using VPC {vpc_id}")
            else:
                for key in instance_keys:
                    update_status_func(key, "ERROR: No VPCs found", is_final=True)
                return []
        else:
            vpc_id = vpcs["Vpcs"][0]["VpcId"]
            for key in instance_keys:
                update_status_func(key, "Using default VPC")
            log_message(f"[{region}] Using default VPC {vpc_id}")

        for key in instance_keys:
            update_status_func(key, "Finding subnet")
        subnets = ec2.describe_subnets(
            Filters=[
                {"Name": "vpc-id", "Values": [vpc_id]},
                {"Name": "default-for-az", "Values": ["true"]},
            ]
        )
        if not subnets["Subnets"]:
            for key in instance_keys:
                update_status_func(key, "Finding any subnet")
            all_subnets = ec2.describe_subnets(
                Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
            )
            if all_subnets["Subnets"]:
                subnet_id = all_subnets["Subnets"][0]["SubnetId"]
                for key in instance_keys:
                    update_status_func(key, "Using subnet")
            else:
                for key in instance_keys:
                    update_status_func(key, "ERROR: No subnets found", is_final=True)
                return []
        else:
            subnet_id = subnets["Subnets"][0]["SubnetId"]
            for key in instance_keys:
                update_status_func(key, "Using default subnet")

        for key in instance_keys:
            update_status_func(key, "Setting up SG")
        sg_id = create_simple_security_group(ec2, vpc_id)

        for key in instance_keys:
            update_status_func(key, "Finding AMI")
        ami_id = get_latest_ubuntu_ami(region, log_message)
        if not ami_id:
            for key in instance_keys:
                update_status_func(key, "ERROR: No AMI found", is_final=True)
            return []

        region_config = config.region_config(region)
        instance_type = region_config.get("machine_type", "t3.medium")
        with lock:
            for key in instance_keys:
                creation_status[key]["type"] = instance_type

        user_data = generate_minimal_cloud_init(config)

        for key in instance_keys:
            update_status_func(key, "Requesting spot")

        security_groups = [sg_id] + config.security_groups()
        spot_request = {
            "ImageId": ami_id,
            "InstanceType": instance_type,
            "SecurityGroupIds": security_groups,
            "SubnetId": subnet_id,
            "UserData": base64.b64encode(user_data.encode()).decode(),
        }
        if config.ssh_key_name():
            spot_request["KeyName"] = config.ssh_key_name()

        # Add IAM instance profile if configured
        iam_profile = config.iam_instance_profile()
        if iam_profile:
            spot_request["IamInstanceProfile"] = {"Name": iam_profile}

        spot_params = {
            "InstanceCount": count,
            "LaunchSpecification": spot_request,
            "Type": "one-time",
        }
        spot_price = region_config.get("spot_price_limit") or config.spot_price_limit()
        if spot_price:
            spot_params["SpotPrice"] = str(spot_price)

        response = ec2.request_spot_instances(**spot_params)
        spot_request_ids = [
            req["SpotInstanceRequestId"] for req in response["SpotInstanceRequests"]
        ]

        for key in instance_keys:
            update_status_func(key, "WAIT: Launching...")

        instances = []
        for attempt in range(30):
            try:
                spot_response = ec2.describe_spot_instance_requests(
                    SpotInstanceRequestIds=spot_request_ids
                )
                active_requests = [
                    req
                    for req in spot_response["SpotInstanceRequests"]
                    if req["State"] == "active" and "InstanceId" in req
                ]

                if len(active_requests) == count:
                    for key in instance_keys:
                        update_status_func(key, "Fetching details")
                    instance_ids = [req["InstanceId"] for req in active_requests]
                    instance_response = ec2.describe_instances(InstanceIds=instance_ids)

                    instance_idx = 0
                    for reservation in instance_response["Reservations"]:
                        for inst in reservation["Instances"]:
                            instances.append(
                                {
                                    "id": inst["InstanceId"],
                                    "region": region,
                                    "type": inst["InstanceType"],
                                    "state": inst["State"]["Name"],
                                    "public_ip": inst.get("PublicIpAddress", ""),
                                    "private_ip": inst.get("PrivateIpAddress", ""),
                                    "created": datetime.now().isoformat(),
                                }
                            )
                            if instance_idx < len(instance_keys):
                                instance_id = inst["InstanceId"]
                                public_ip = inst.get("PublicIpAddress", "")
                                private_ip = inst.get("PrivateIpAddress", "")
                                
                                # Use public IP if available, otherwise fall back to private IP
                                display_ip = public_ip if public_ip else private_ip
                                
                                # Update the console logger's IP map if available
                                if hasattr(logger, 'console_handler') and display_ip:
                                    logger.console_handler.instance_ip_map[instance_id] = display_ip
                                
                                # Debug: Log what we're sending
                                logger.debug(f"Calling update_status_func with: key={instance_keys[instance_idx]}, id={instance_id}, ip={display_ip}")
                                
                                update_status_func(
                                    instance_keys[instance_idx],
                                    "SUCCESS: Created",
                                    instance_id,
                                    display_ip,
                                    datetime.now().isoformat(),
                                    is_final=True,
                                )
                                instance_idx += 1

                    if instance_ids:
                        tags = [
                            {"Key": "ManagedBy", "Value": "SpotDeployer"},
                            {"Key": "Name", "Value": f"SpotInstance-{region}"},
                        ]
                        tags.extend(
                            [{"Key": k, "Value": v} for k, v in config.tags().items()]
                        )
                        tags.extend(
                            [
                                {"Key": k, "Value": v}
                                for k, v in region_config.get("tags", {}).items()
                            ]
                        )
                        ec2.create_tags(Resources=instance_ids, Tags=tags)
                    break

                if any(
                    req["State"] in ["failed", "cancelled"]
                    for req in spot_response["SpotInstanceRequests"]
                ):
                    for key in instance_keys:
                        update_status_func(key, "ERROR: Spot failed", is_final=True)
                    break

                for key in instance_keys:
                    update_status_func(key, f"WAIT: Spot wait ({attempt + 1}/30)")
                time.sleep(10)
            except Exception as e:
                if "InvalidSpotInstanceRequestID.NotFound" in str(e):
                    for key in instance_keys:
                        update_status_func(
                            key, "ERROR: Spot Request Expired/Invalid", is_final=True
                        )
                    log_message(
                        f"[{region}] Spot request ID not found. It likely failed immediately. Check AWS console for reason."
                    )
                else:
                    for key in instance_keys:
                        update_status_func(key, f"ERROR: {e}", is_final=True)
                break

        if not instances:
            for key in instance_keys:
                update_status_func(key, "ERROR: Timeout", is_final=True)

        return instances

    except Exception as e:
        for key in instance_keys:
            update_status_func(key, f"ERROR: {e}", is_final=True)
        return []


# =============================================================================
# MAIN COMMANDS
# =============================================================================


def post_creation_setup(
    instances, config, update_status_func, logger, progress_callback=None
):
    """Simplified hands-off setup - upload files, enable service, and disconnect."""

    def setup_instance(instance):
        key = instance["id"]
        ip = instance.get("public_ip")
        username = config.username()
        private_key_path = os.path.expanduser(config.private_ssh_key_path())

        if not ip:
            update_status_func(key, "ERROR: No public IP", is_final=True)
            return

        try:
            # Phase 1: Wait for basic SSH (no cloud-init monitoring)
            update_status_func(key, "SSH: Waiting for connection...")
            logger.info(f"Waiting for SSH on {key} at {ip}")

            if not wait_for_ssh_only(ip, username, private_key_path, timeout=30):
                update_status_func(key, "ERROR: SSH timeout", is_final=True)
                logger.error(f"SSH timeout for {key}")
                return

            update_status_func(key, "SSH: Connected")
            logger.info(f"SSH available for {key}")

            # Phase 2: Create directories (separate from upload)
            update_status_func(key, "SETUP: Creating directories...")
            logger.info(f"Creating remote directories on {key}")

            if not ensure_remote_directories(ip, username, private_key_path, logger):
                update_status_func(
                    key, "ERROR: Directory creation failed", is_final=True
                )
                logger.error(f"Directory creation failed for {key}")
                return

            update_status_func(key, "SETUP: Directories ready")
            logger.info(f"Directories created successfully on {key}")

            # Phase 3: Upload files
            update_status_func(key, "UPLOAD: Transferring files...")
            logger.info(
                f"Starting file upload to {key} at {ip} with key {private_key_path}"
            )

            # Pass the update_status_func to upload_files_to_instance
            upload_files_to_instance.update_status_func = update_status_func
            
            if not upload_files_to_instance(
                ip,
                username,
                private_key_path,
                config,
                logger,
                progress_callback=None,  # No detailed progress in hands-off mode
                instance_key=key,
            ):
                update_status_func(key, "ERROR: File upload failed", is_final=True)
                logger.error(
                    f"File upload failed for {key} - check permissions and SSH key"
                )
                return

            update_status_func(key, "UPLOAD: Files transferred")
            logger.info(f"Files uploaded to {key}")

            # Phase 4: Configure and start services
            update_status_func(key, "SETUP: Configuring services...")
            if not enable_startup_service(ip, username, private_key_path, logger):
                update_status_func(key, "ERROR: Service configuration failed", is_final=True)
                logger.error(f"Service configuration failed for {key}")
                return

            # Phase 5: Setup complete
            update_status_func(
                key,
                "SUCCESS: Setup complete - services starting",
                is_final=True,
            )
            logger.info(
                f"Setup complete for {key} - services are starting"
            )

        except Exception as e:
            logger.error(f"Error setting up instance {key}: {e}")
            update_status_func(key, f"ERROR: {e}", is_final=True)

    threads = []
    for instance in instances:
        thread = threading.Thread(
            target=setup_instance, args=(instance,), name=f"Setup-{instance['id']}"
        )
        thread.daemon = False  # Changed to non-daemon so main thread waits
        threads.append(thread)
        thread.start()

    # Wait for setup threads - shorter timeout since we're not waiting for cloud-init
    # This ensures all file uploads complete before we return
    for thread in threads:
        thread.join(timeout=180)  # 3 minute timeout

    # Log completion
    if logger:
        logger.info("All post-creation setup tasks completed")


def cmd_create(config: SimpleConfig, state: SimpleStateManager) -> None:
    """Create spot instances across configured regions with enhanced real-time progress tracking."""
    if not check_aws_auth():
        return

    # Show helpful info about the deployment process
    console.print("\n[bold cyan]🚀 Starting AWS Spot Instance Deployment[/bold cyan]")
    console.print("\n[bold]Hands-off Deployment Process:[/bold]")
    console.print(
        "1. [yellow]Create Instances[/yellow] - Request spot instances from AWS"
    )
    console.print("2. [blue]Wait for SSH[/blue] - Basic connectivity check")
    console.print("3. [green]Upload Files[/green] - Transfer scripts and configuration")
    console.print("4. [magenta]Enable Service[/magenta] - Set up systemd service")
    console.print("5. [cyan]Disconnect[/cyan] - Let cloud-init complete autonomously")
    console.print(
        "\n[dim]After ~5 minutes, instances will be fully configured and running.[/dim]\n"
    )

    # Setup local logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"spot_creation_{timestamp}.log"
    logger = logging.getLogger("spot_creator")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        # File handler
        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(threadName)s - %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Console handler to capture thread output with instance context
        # Note: We'll update the IP map as instances are created
        console_handler = ConsoleLogger(console, {})
        console_formatter = logging.Formatter("%(message)s")
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # Store reference to console handler for updating IP map
        logger.console_handler = console_handler

    rich_status(f"Logging to local file: {log_filename}")
    logger.info(
        f"Using column widths: REGION={ColumnWidths.REGION}, INSTANCE_ID={ColumnWidths.INSTANCE_ID}, "
        f"STATUS={ColumnWidths.STATUS}, TYPE={ColumnWidths.TYPE}, PUBLIC_IP={ColumnWidths.PUBLIC_IP}, "
        f"CREATED={ColumnWidths.CREATED}, TOTAL={ColumnWidths.get_total_width()}"
    )

    # Check for SSH key
    private_key_path = config.private_ssh_key_path()
    if private_key_path:
        expanded_path = os.path.expanduser(private_key_path)
        if not os.path.exists(expanded_path):
            rich_error(f"Private SSH key not found at '{private_key_path}'")
            rich_status(
                "Please check your config.yaml or generate a new key, e.g.: ssh-keygen -t rsa -b 2048"
            )
            return
    else:
        rich_warning(
            "Private SSH key path is not set in config.yaml. SSH-based operations will fail."
        )

    regions = config.regions()

    if not regions:
        rich_error("No regions configured. Run 'setup' first.")
        return

    # Get instance counts per region
    region_instance_map = {}
    total_instances_to_create = 0
    for region in regions:
        region_cfg = config.region_config(region)
        count = region_cfg.get("instances_per_region", 1)
        region_instance_map[region] = count
        total_instances_to_create += count

    if total_instances_to_create == 0:
        rich_warning("No instances configured to be created.")
        return

    total_created = 0
    if RICH_AVAILABLE and console:
        # --- Enhanced Centralized State and UI Management with Progress Tracking ---
        creation_status = {}
        all_instances = []
        active_threads = []
        lock = threading.Lock()

        # Initialize ProgressTracker
        progress_tracker = ProgressTracker()
        overall_task = progress_tracker.create_overall_progress(
            total_instances_to_create
        )

        # Initialize status for each instance
        for region, count in region_instance_map.items():
            region_cfg = config.region_config(region)
            instance_type = region_cfg.get("machine_type", "t3.medium")
            for i in range(count):
                key = f"{region}-{i + 1}"
                creation_status[key] = {
                    "region": region,
                    "instance_id": "pending...",
                    "status": "WAIT: Starting...",
                    "type": instance_type,
                    "public_ip": "pending...",
                    "created": "pending...",
                }
                # Create individual progress bars for detailed tracking
                progress_tracker.create_instance_progress(
                    key, f"{key} - Initializing..."
                )

        def generate_layout():
            # Create the table with fixed widths from constants
            table = Table(
                title=f"Creating {total_instances_to_create} instances across {len(regions)} regions",
                show_header=True,
                width=ColumnWidths.get_total_width(),
            )
            table.add_column(
                "Region", style="magenta", width=ColumnWidths.REGION, no_wrap=True
            )
            table.add_column(
                "Instance ID",
                style="cyan",
                width=ColumnWidths.INSTANCE_ID,
                no_wrap=True,
            )
            table.add_column(
                "Status", style="yellow", width=ColumnWidths.STATUS, no_wrap=True
            )
            table.add_column(
                "Type", style="green", width=ColumnWidths.TYPE, no_wrap=True
            )
            table.add_column(
                "Public IP", style="blue", width=ColumnWidths.PUBLIC_IP, no_wrap=True
            )
            table.add_column(
                "Created", style="dim", width=ColumnWidths.CREATED, no_wrap=True
            )

            sorted_items = sorted(creation_status.items(), key=lambda x: x[0])

            for key, item in sorted_items:
                status = item["status"]
                max_len = ColumnWidths.STATUS - 1
                if len(status) > max_len:
                    status = status[: max_len - 3] + "..."

                if status.startswith("SUCCESS"):
                    status_style = "[bold green]" + status + "[/bold green]"
                elif status.startswith("ERROR"):
                    status_style = "[bold red]" + status + "[/bold red]"
                else:
                    status_style = status

                table.add_row(
                    item["region"],
                    item["instance_id"],
                    status_style,
                    item["type"],
                    item["public_ip"],
                    item["created"],
                )

            # Read last 10 lines from the log file
            try:
                with open(log_filename, 'r') as f:
                    # Read all lines and get the last 10
                    lines = f.readlines()
                    last_lines = lines[-10:] if len(lines) >= 10 else lines
                    # Strip newlines and format
                    formatted_messages = [line.strip() for line in last_lines if line.strip()]
                    log_content = "\n".join(formatted_messages)
            except (FileNotFoundError, IOError):
                log_content = "Waiting for log entries..."
            
            log_panel = Panel(
                log_content, title="On-Screen Log", border_style="blue", height=12
            )

            layout = Layout()
            layout.split_column(
                Layout(table, name="table", ratio=2),
                Layout(log_panel, name="logs", ratio=1),
            )
            return layout

        def update_progress_callback(instance_key, phase, progress, status=""):
            """Callback function to update progress tracking."""
            progress_tracker.update_instance_progress(
                instance_key, phase, progress, status
            )

            # Update overall progress
            if progress_tracker.overall_progress:
                completed_instances = 0
                for key in creation_status:
                    if creation_status[key]["status"].startswith("SUCCESS"):
                        completed_instances += 1

                # Each instance contributes 6 phases to overall progress
                phases_per_instance = 6
                current_phase = (completed_instances * phases_per_instance) + (
                    progress / 100.0
                )
                progress_tracker.overall_progress.update(
                    overall_task, completed=current_phase
                )

        with Live(
            generate_layout(),
            refresh_per_second=3.33,
            console=console,
            screen=False,
            transient=True,
        ) as live:

            def update_status(
                instance_key: str,
                status: str,
                instance_id: str = None,
                ip: str = None,
                created: str = None,
                is_final=False,
            ):
                """Centralized function to update UI and log full messages."""
                with lock:
                    full_status = status.replace("\n", " ").replace("\r", " ").strip()
                    
                    # Create the log message with instance ID and IP if available
                    if instance_id and ip and "SUCCESS:" in status:
                        # Update the console logger's IP map if available
                        if hasattr(logger, 'console_handler'):
                            logger.console_handler.instance_ip_map[instance_id] = ip
                        # Log with instance ID and IP in the message
                        logger.info(f"[{instance_id} @ {ip}] {full_status}")
                    elif "ERROR:" in status and instance_id and ip:
                        # Also include instance ID and IP for errors
                        if hasattr(logger, 'console_handler'):
                            logger.console_handler.instance_ip_map[instance_id] = ip
                        logger.info(f"[{instance_id} @ {ip}] {full_status}")
                    else:
                        logger.info(f"[{instance_key}] Status: '{full_status}'")

                    if instance_key in creation_status:
                        creation_status[instance_key]["status"] = full_status
                        if instance_id:
                            creation_status[instance_key]["instance_id"] = instance_id
                        if ip:
                            creation_status[instance_key]["public_ip"] = ip
                        if created:
                            creation_status[instance_key]["created"] = created

            def create_region_instances(region, instances_count, logger):
                try:
                    logger.info(f"Starting creation for {region}...")
                    instances = create_instances_in_region_with_table(
                        config,
                        region,
                        instances_count,
                        creation_status,
                        lock,
                        logger,
                        update_status,
                    )
                    with lock:
                        all_instances.extend(instances)
                    if instances and config.private_ssh_key_path():
                        post_creation_setup(
                            instances,
                            config,
                            update_status,
                            logger,
                            progress_callback=update_progress_callback,
                        )
                except Exception:
                    logger.error(f"Error in thread for {region}", exc_info=True)

            for region, count in region_instance_map.items():
                thread = threading.Thread(
                    target=create_region_instances,
                    args=(region, count, logger),
                    name=f"Region-{region}",
                )
                thread.daemon = False  # Changed to non-daemon so we wait for completion
                active_threads.append(thread)
                thread.start()

            # Periodically update the display while threads are running
            while any(t.is_alive() for t in active_threads):
                live.update(generate_layout())
                time.sleep(0.3)

            # Final update
            live.update(generate_layout())

            with lock:
                logger.info("All tasks complete.")

        # Save all instances to state and count them
        for instance in all_instances:
            state.add_instance(instance)
            total_created += 1

        console.print("\n")
        rich_success(f"Successfully created {total_created} instances!")

        if total_created > 0:
            # Show current state
            console.print("\n")
            cmd_list(state)

            # Wait a moment to ensure all setup threads have finished
            console.print(
                "\n[bold yellow]⏳ Waiting for file uploads to complete...[/bold yellow]"
            )
            console.print("[dim]Setup status is shown in the table above.[/dim]")

            # Show a spinner while waiting
            with console.status(
                "[cyan]Finishing setup tasks...[/cyan]", spinner="dots"
            ):
                # Wait for any remaining threads
                start_wait = time.time()
                for thread in active_threads:
                    if thread.is_alive():
                        remaining_timeout = max(1, 30 - (time.time() - start_wait))
                        thread.join(timeout=remaining_timeout)

            # Final completion message
            console.print("\n[bold green]✅ Deployment Complete![/bold green]")
            console.print("\n[yellow]What happens next:[/yellow]")
            console.print("• Cloud-init is installing packages and Docker")
            console.print("• System will reboot automatically when ready")
            console.print("• Startup services will begin after reboot")
            console.print(
                "\n[dim]Check back in ~5 minutes. Your instances are configuring themselves.[/dim]\n"
            )
    else:
        # Fallback without table
        for region, count in region_instance_map.items():
            instances = create_instances_in_region(config, region, count)
            for instance in instances:
                state.add_instance(instance)
                total_created += 1
                rich_success(f"Created {instance['id']} in {region}")
        rich_success(f"Successfully created {total_created} instances")


def cmd_list(state: SimpleStateManager) -> None:
    """List all managed instances with Rich table."""
    if not check_aws_auth():
        return

    instances = state.load_instances()

    if not instances:
        rich_status("No instances found")
        return
    
    # Sync state with AWS to detect terminated instances - do this in parallel by region
    instances_to_remove = []
    instance_lock = threading.Lock()
    
    # Group instances by region for more efficient API calls
    instances_by_region = {}
    for instance in instances:
        region = instance["region"]
        if region not in instances_by_region:
            instances_by_region[region] = []
        instances_by_region[region].append(instance)
    
    def check_region_instances(region, region_instances):
        """Check all instances in a region with a single API call."""
        try:
            ec2 = boto3.client("ec2", region_name=region)
            instance_ids = [inst["id"] for inst in region_instances]
            
            # Get all instances in one call
            response = ec2.describe_instances(InstanceIds=instance_ids)
            
            # Build a map of instance data
            instance_data_map = {}
            for reservation in response["Reservations"]:
                for inst_data in reservation["Instances"]:
                    instance_data_map[inst_data["InstanceId"]] = inst_data
            
            # Update each instance
            for instance in region_instances:
                if instance["id"] in instance_data_map:
                    inst_data = instance_data_map[instance["id"]]
                    current_state = inst_data["State"]["Name"]
                    instance["state"] = current_state
                    
                    # Update public IP if available
                    if "PublicIpAddress" in inst_data:
                        instance["public_ip"] = inst_data["PublicIpAddress"]
                    
                    # Mark terminated instances for removal
                    if current_state == "terminated":
                        with instance_lock:
                            instances_to_remove.append(instance)
                else:
                    # Instance not found in response
                    with instance_lock:
                        instances_to_remove.append(instance)
                        
        except Exception as e:
            # If we get InvalidInstanceID error, check which instances are invalid
            if "InvalidInstanceID" in str(e):
                # Try instances one by one to find the invalid ones
                for instance in region_instances:
                    try:
                        response = ec2.describe_instances(InstanceIds=[instance["id"]])
                        if not response["Reservations"]:
                            with instance_lock:
                                instances_to_remove.append(instance)
                    except Exception:
                        with instance_lock:
                            instances_to_remove.append(instance)
            else:
                # For other errors, mark all instances in region as unknown
                for instance in region_instances:
                    instance["state"] = "unknown"
    
    # Create threads for parallel checking by region
    threads = []
    for region, region_instances in instances_by_region.items():
        thread = threading.Thread(target=check_region_instances, args=(region, region_instances))
        thread.daemon = True
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join(timeout=15)  # 15 second timeout per region
    
    # Remove terminated instances from state
    if instances_to_remove:
        for inst in instances_to_remove:
            instances.remove(inst)
        state.save_instances(instances)
        rich_warning(f"Removed {len(instances_to_remove)} terminated instances from state")
    
    if not instances:
        rich_status("No active instances found")
        return

    if RICH_AVAILABLE and console:
        # Create beautiful Rich table with consistent widths
        table = Table(
            title=f"Managed Instances ({len(instances)} total)",
            show_header=True,
            width=ColumnWidths.get_total_width(),
        )
        table.add_column(
            "Instance ID", style="cyan", width=ColumnWidths.INSTANCE_ID, no_wrap=True
        )
        table.add_column(
            "Region", style="magenta", width=ColumnWidths.REGION, no_wrap=True
        )
        table.add_column("Type", style="green", width=ColumnWidths.TYPE, no_wrap=True)
        table.add_column(
            "State", style="yellow", width=ColumnWidths.STATUS, no_wrap=False
        )
        table.add_column(
            "Public IP", style="blue", width=ColumnWidths.PUBLIC_IP, no_wrap=True
        )
        table.add_column(
            "Created", style="dim", width=ColumnWidths.CREATED, no_wrap=True
        )

        for instance in instances:
            # Style state column
            state_text = instance.get("state", "unknown")
            if state_text == "running":
                state_style = "[bold green]running[/bold green]"
            elif state_text == "pending":
                state_style = "[bold yellow]pending[/bold yellow]"
            elif state_text in ["stopped", "terminated"]:
                state_style = "[bold red]" + state_text + "[/bold red]"
            else:
                state_style = state_text

            table.add_row(
                instance["id"],
                instance["region"],
                instance["type"],
                state_style,
                instance.get("public_ip", "N/A"),
                instance.get("created", "Unknown"),
            )

        console.print(table)
    else:
        # Fallback to simple table
        print(f"\nManaged Instances ({len(instances)} total):")
        print("-" * 90)
        print(
            f"{'ID':<20} {'Region':<15} {'Type':<12} {'State':<10} {'Public IP':<15} {'Created':<28}"
        )
        print("-" * 90)

        for instance in instances:
            print(
                f"{instance['id']:<20} {instance['region']:<15} {instance['type']:<12} "
                f"{instance['state']:<10} {instance.get('public_ip', 'N/A'):<15} {instance.get('created', 'Unknown'):<28}"
            )


def cmd_random_instance(state: SimpleStateManager, config: SimpleConfig) -> None:
    """Get a random instance and print SSH command."""
    if not check_aws_auth():
        return

    instances = state.load_instances()

    # Filter for running instances that have a public IP
    running_instances = [
        inst
        for inst in instances
        if inst.get("public_ip") and inst.get("state") == "running"
    ]

    if not running_instances:
        rich_status("No running instances with a public IP were found.")
        return

    # Select one random instance
    random_instance = random.choice(running_instances)

    username = config.username()
    ip_address = random_instance["public_ip"]

    # Construct the SSH command
    ssh_command = f'ssh -o "UserKnownHostsFile=/dev/null" -o "StrictHostKeyChecking=no" {username}@{ip_address}'

    rich_print(
        f"\n[bold]SSH command for random instance [cyan]({random_instance['id']})[/cyan]:[/bold]"
    )
    rich_print(ssh_command, style="yellow")


def cmd_print_log(state: SimpleStateManager, config: SimpleConfig) -> None:
    """Print startup log from a random instance."""
    if not check_aws_auth():
        return

    instances = state.load_instances()

    # Filter for running instances that have a public IP
    running_instances = [
        inst
        for inst in instances
        if inst.get("public_ip") and inst.get("state") == "running"
    ]

    if not running_instances:
        rich_status("No running instances with a public IP were found.")
        return

    # Select one random instance
    random_instance = random.choice(running_instances)

    username = config.username()
    ip_address = random_instance["public_ip"]
    private_key_path = os.path.expanduser(config.private_ssh_key_path())

    rich_print(
        f"\n[bold cyan]Fetching startup log from instance {random_instance['id']} ({ip_address})...[/bold cyan]\n"
    )

    # SSH command to get the log
    ssh_command = [
        "ssh",
        "-i",
        private_key_path,
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "ConnectTimeout=10",
        f"{username}@{ip_address}",
        "sudo cat /opt/startup.log 2>/dev/null || echo 'Log file not found'",
    ]

    try:
        result = subprocess.run(ssh_command, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(result.stdout)
        else:
            rich_error(f"Failed to fetch log: {result.stderr}")
    except subprocess.TimeoutExpired:
        rich_error("Connection timeout - instance may not be ready yet")
    except Exception as e:
        rich_error(f"Error fetching log: {e}")


def cmd_debug_log(state: SimpleStateManager, config: SimpleConfig) -> None:
    """Print comprehensive debug information from a random instance."""
    if not check_aws_auth():
        return

    instances = state.load_instances()

    # Filter for running instances that have a public IP
    running_instances = [
        inst
        for inst in instances
        if inst.get("public_ip") and inst.get("state") == "running"
    ]

    if not running_instances:
        rich_status("No running instances with a public IP were found.")
        return

    # Select one random instance
    random_instance = random.choice(running_instances)

    username = config.username()
    ip_address = random_instance["public_ip"]
    private_key_path = os.path.expanduser(config.private_ssh_key_path())

    rich_print(
        f"\n[bold cyan]Fetching debug information from instance {random_instance['id']} ({ip_address})...[/bold cyan]\n"
    )

    # Debug commands to run
    debug_script = """
echo "=== DEBUG LOG COLLECTION $(date) ==="
echo ""
echo "=== System Info ==="
echo "Hostname: $(hostname)"
echo "Uptime: $(uptime)"
echo "User: $(whoami)"
echo ""
echo "=== Systemd Service Status ==="
sudo systemctl status --no-pager bacalhau-startup.service
echo "---"
sudo systemctl status --no-pager setup-config.service  
echo "---"
sudo systemctl status --no-pager bacalhau.service
echo "---"
sudo systemctl status --no-pager sensor-generator.service
echo ""
echo "=== Docker Status ==="
docker version 2>&1 || echo "Docker not available"
echo "---"
docker ps -a
echo ""
echo "=== Main Startup Log (/opt/startup.log) ==="
if [ -f /opt/startup.log ]; then
    echo "--- Last 50 lines ---"
    sudo tail -50 /opt/startup.log
else
    echo "File not found: /opt/startup.log"
fi
echo ""
echo "=== Configuration Files Check ==="
ls -la /bacalhau_node/ 2>&1 || echo "/bacalhau_node/ not found"
echo "---"
ls -la /opt/sensor/config/ 2>&1 || echo "/opt/sensor/config/ not found"
echo ""
echo "=== Cloud-init Status ==="
cloud-init status --long 2>&1 || echo "cloud-init status not available"
echo ""
echo "=== END DEBUG LOG COLLECTION ==="
"""

    # SSH command to run the debug script
    ssh_command = [
        "ssh",
        "-i",
        private_key_path,
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "ConnectTimeout=10",
        f"{username}@{ip_address}",
        debug_script,
    ]

    try:
        result = subprocess.run(ssh_command, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print(result.stdout)
        else:
            rich_error(f"Failed to fetch debug info: {result.stderr}")
    except subprocess.TimeoutExpired:
        rich_error("Connection timeout - instance may not be ready yet")
    except Exception as e:
        rich_error(f"Error fetching debug info: {e}")


def cmd_destroy(state: SimpleStateManager) -> None:
    """Destroy all managed instances and clean up all created resources with enhanced progress tracking."""
    if not check_aws_auth():
        return

    instances = state.load_instances()

    if not instances:
        rich_status("No instances to destroy")
        # Still try to clean up any orphaned VPCs
        _cleanup_vpcs()
        return

    if RICH_AVAILABLE and console:
        # Initialize progress tracking for destruction
        progress_tracker = ProgressTracker()
        overall_task = progress_tracker.create_overall_progress(len(instances))

        # Set up logging to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"spot_destroy_{timestamp}.log"
        logger = logging.getLogger("spot_destroyer")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            # File handler
            file_handler = logging.FileHandler(log_filename)
            file_handler.setLevel(logging.INFO)
            formatter = logging.Formatter("%(asctime)s - %(message)s")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
            # Console handler
            console_handler = ConsoleLogger(console, {})
            console_formatter = logging.Formatter("%(message)s")
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)

        # Create live-updating table for destruction progress
        destruction_status = {}
        for instance in instances:
            key = instance["id"]
            destruction_status[key] = {
                "region": instance["region"],
                "instance_id": instance["id"],
                "status": "🔄 Preparing...",
                "type": instance["type"],
                "public_ip": instance.get("public_ip", "N/A"),
                "created": instance.get("created", "Unknown"),
            }
            # Create individual progress bars
            progress_tracker.create_instance_progress(
                key, f"{key} - Preparing to terminate"
            )

        def generate_destroy_layout():
            # Create the table
            table = Table(
                title=f"Destroying {len(instances)} instances",
                show_header=True,
                width=ColumnWidths.get_total_width(),
            )
            table.add_column(
                "Region", style="magenta", width=ColumnWidths.REGION, no_wrap=True
            )
            table.add_column(
                "Instance ID",
                style="cyan",
                width=ColumnWidths.INSTANCE_ID,
                no_wrap=True,
            )
            table.add_column(
                "Status", style="yellow", width=ColumnWidths.STATUS, no_wrap=True
            )
            table.add_column(
                "Type", style="green", width=ColumnWidths.TYPE, no_wrap=True
            )
            table.add_column(
                "Public IP", style="blue", width=ColumnWidths.PUBLIC_IP, no_wrap=True
            )
            table.add_column(
                "Created", style="dim", width=ColumnWidths.CREATED, no_wrap=True
            )

            # Sort: active work at top, completed at bottom
            sorted_items = sorted(
                destruction_status.items(),
                key=lambda x: (
                    0 if x[1]["status"].startswith("SUCCESS") else 1,
                    1 if x[1]["status"].startswith("ERROR") else 0,
                    x[0],
                ),
            )

            for key, item in sorted_items:
                # Truncate status
                status = item["status"]
                max_len = ColumnWidths.STATUS - 2
                if len(status) > max_len:
                    status = status[:max_len] + "..."

                if "terminated" in status.lower() or "success" in status.lower():
                    status_style = "[bold green]" + status + "[/bold green]"
                elif "error" in status.lower() or "failed" in status.lower():
                    status_style = "[bold red]" + status + "[/bold red]"
                else:
                    status_style = status

                table.add_row(
                    item["region"],
                    item["instance_id"],
                    status_style,
                    item["type"],
                    item["public_ip"],
                    item.get("created", "Unknown"),
                )

            # Create the log panel - read from log file
            # Note: log_filename is already defined at the function level
            try:
                with open(log_filename, 'r') as f:
                    lines = f.readlines()
                    # Get last 20 lines
                    last_lines = lines[-20:] if len(lines) >= 20 else lines
                    formatted_messages = [line.strip() for line in last_lines if line.strip()]
                    log_content = "\n".join(formatted_messages)
            except (FileNotFoundError, IOError):
                log_content = "Waiting for log entries..."
                
            log_panel = Panel(
                log_content, title="📋 Log Messages", border_style="blue", height=8
            )

            # Create layout
            layout = Layout()
            layout.split_column(
                Layout(table, name="table", ratio=3),
                Layout(log_panel, name="logs", ratio=1),
            )

            return layout

        def update_destruction_progress(instance_key, phase, progress, status=""):
            """Callback for destruction progress updates."""
            progress_tracker.update_instance_progress(
                instance_key, phase, progress, status
            )

            # Update overall destruction progress
            if progress_tracker.overall_progress:
                completed_instances = 0
                for key in destruction_status:
                    if "terminated" in destruction_status[key]["status"].lower():
                        completed_instances += 1

                current_phase = completed_instances + (progress / 100.0)
                progress_tracker.overall_progress.update(
                    overall_task, completed=current_phase
                )

        # Group by region
        by_region = {}
        for instance in instances:
            region = instance["region"]
            if region not in by_region:
                by_region[region] = []
            by_region[region].append(instance)

        with Live(
            generate_destroy_layout(),
            refresh_per_second=2,
            console=console,
            screen=True,
        ):
            total_terminated = 0
            for region, region_instances in by_region.items():
                try:
                    logger.info(
                        f"Terminating {len(region_instances)} instances in {region}..."
                    )
                    ec2 = boto3.client("ec2", region_name=region)
                    instance_ids = [inst["id"] for inst in region_instances]

                    # Update status for all instances in this region
                    for instance in region_instances:
                        destruction_status[instance["id"]]["status"] = (
                            "🔄 Terminating..."
                        )
                        update_destruction_progress(
                            instance["id"],
                            "Termination",
                            50,
                            "Requesting termination...",
                        )

                    time.sleep(1)  # Show the terminating status

                    # Terminate instances
                    try:
                        ec2.terminate_instances(InstanceIds=instance_ids)
                        logger.info(
                            f"Successfully terminated {len(instance_ids)} instances in {region}"
                        )

                        # Update status to completed
                        for instance in region_instances:
                            destruction_status[instance["id"]]["status"] = "✅ Terminated"
                            update_destruction_progress(
                                instance["id"],
                                "Termination",
                                100,
                                "Successfully terminated",
                            )
                    except Exception as term_error:
                        # Check if it's because instances don't exist
                        error_str = str(term_error)
                        if "InvalidInstanceID" in error_str:
                            logger.info(
                                f"Some instances in {region} no longer exist in AWS (already terminated)"
                            )
                            # Mark as terminated anyway since they don't exist
                            for instance in region_instances:
                                destruction_status[instance["id"]]["status"] = "✅ Already terminated"
                                update_destruction_progress(
                                    instance["id"],
                                    "Termination",
                                    100,
                                    "Instance already terminated",
                                )
                        else:
                            # Re-raise for other errors
                            raise term_error

                    # Always remove from state, even if already terminated in AWS
                    removed = state.remove_instances_by_region(region)
                    total_terminated += removed

                    time.sleep(1)  # Show the completed status

                except Exception as e:
                    logger.info(f"Error terminating instances in {region}: {e}")
                    # Update status to failed
                    for instance in region_instances:
                        destruction_status[instance["id"]]["status"] = (
                            f"❌ Error: {str(e)[:15]}..."
                        )
                        update_destruction_progress(
                            instance["id"], "Termination", 0, f"Failed: {str(e)}"
                        )

                    time.sleep(1)  # Show the error status

            # Final update
            time.sleep(2)
    else:
        # Fallback without table
        by_region = {}
        for instance in instances:
            region = instance["region"]
            if region not in by_region:
                by_region[region] = []
            by_region[region].append(instance["id"])

        total_terminated = 0
        for region, instance_ids in by_region.items():
            try:
                ec2 = boto3.client("ec2", region_name=region)
                try:
                    ec2.terminate_instances(InstanceIds=instance_ids)
                    rich_success(f"Terminated {len(instance_ids)} instances in {region}")
                except Exception as term_error:
                    # Check if it's because instances don't exist
                    if "InvalidInstanceID" in str(term_error):
                        rich_warning(f"Some instances in {region} no longer exist in AWS (already terminated)")
                    else:
                        raise term_error
                
                # Always remove from state, even if already terminated
                removed = state.remove_instances_by_region(region)
                total_terminated += removed
            except Exception as e:
                rich_error(f"Error terminating instances in {region}: {e}")

    rich_success(f"Successfully terminated {total_terminated} instances")

    # Clean up VPCs and other resources
    _cleanup_vpcs()


def cmd_nuke(state: SimpleStateManager) -> None:
    """Destroy all managed instances and resources by querying the AWS API directly.

    This function bypasses local state and queries AWS directly to find and terminate
    all instances tagged with 'ManagedBy: SpotDeployer'. Use this when the destroy
    command fails or when local state is inconsistent with AWS reality.
    """
    if not check_aws_auth():
        return

    # Show current local state for comparison
    local_instances = state.load_instances()
    if local_instances:
        rich_status(
            f"Local state shows {len(local_instances)} instances, but we'll query AWS directly."
        )

    rich_warning(
        "🚨 DESTRUCTIVE OPERATION: This will terminate ALL instances with the 'ManagedBy: SpotDeployer' tag."
    )
    rich_warning(
        "This queries AWS directly and ignores local state. Use this to recover from state inconsistencies."
    )
    if input("Are you sure you want to continue? (y/n): ").lower() != "y":
        rich_status("Nuke operation cancelled.")
        return

    config = SimpleConfig()
    all_regions = [list(r.keys())[0] for r in config.data.get("regions", [])]

    if not all_regions:
        try:
            ec2_client = boto3.client("ec2")
            aws_regions = [
                region["RegionName"]
                for region in ec2_client.describe_regions()["Regions"]
            ]
            all_regions = aws_regions
        except Exception as e:
            rich_error(f"Could not fetch AWS regions: {e}")
            return

    # Scan for instances in parallel
    instances_to_terminate = []
    scan_lock = threading.Lock()
    
    def scan_region(region):
        """Scan a single region for instances to terminate."""
        try:
            ec2 = boto3.client("ec2", region_name=region)
            response = ec2.describe_instances(
                Filters=[
                    {"Name": "tag:ManagedBy", "Values": ["SpotDeployer"]},
                    {
                        "Name": "instance-state-name",
                        "Values": ["pending", "running", "stopping", "stopped"],
                    },
                ]
            )
            region_instances = []
            for reservation in response["Reservations"]:
                for instance in reservation["Instances"]:
                    region_instances.append(
                        {"id": instance["InstanceId"], "region": region}
                    )
            
            if region_instances:
                with scan_lock:
                    instances_to_terminate.extend(region_instances)
                    
        except Exception as e:
            rich_warning(f"Could not scan {region}: {e}")
    
    # Create progress display
    if RICH_AVAILABLE and console:
        console.print(f"\n[bold cyan]Scanning {len(all_regions)} regions in parallel...[/bold cyan]")
        
        # Create threads for parallel scanning
        scan_threads = []
        start_time = time.time()
        
        for region in all_regions:
            thread = threading.Thread(target=scan_region, args=(region,))
            thread.daemon = True
            scan_threads.append(thread)
            thread.start()
        
        # Show spinner while waiting
        with console.status("[cyan]Scanning AWS regions for managed instances...[/cyan]", spinner="dots"):
            for thread in scan_threads:
                thread.join(timeout=30)  # 30 second timeout per region
        
        scan_time = time.time() - start_time
        console.print(f"[green]✓ Completed scanning in {scan_time:.1f} seconds[/green]")
    else:
        # Fallback without fancy display
        scan_threads = []
        for region in all_regions:
            thread = threading.Thread(target=scan_region, args=(region,))
            thread.daemon = True
            scan_threads.append(thread)
            thread.start()
        
        for thread in scan_threads:
            thread.join(timeout=30)

    if not instances_to_terminate:
        rich_success("No managed instances found to nuke.")
        _cleanup_vpcs()
        return

    rich_status(f"Found {len(instances_to_terminate)} instances to terminate.")

    by_region = {}
    for inst in instances_to_terminate:
        if inst["region"] not in by_region:
            by_region[inst["region"]] = []
        by_region[inst["region"]].append(inst["id"])

    # Terminate instances in parallel
    total_terminated = 0
    terminate_lock = threading.Lock()
    termination_results = []
    
    def terminate_region_instances(region, instance_ids):
        """Terminate all instances in a region."""
        try:
            ec2 = boto3.client("ec2", region_name=region)
            ec2.terminate_instances(InstanceIds=instance_ids)
            
            with terminate_lock:
                nonlocal total_terminated
                total_terminated += len(instance_ids)
                termination_results.append((region, len(instance_ids), "success", None))
                
        except Exception as e:
            with terminate_lock:
                termination_results.append((region, len(instance_ids), "error", str(e)))
    
    # Create threads for parallel termination
    if RICH_AVAILABLE and console:
        console.print(f"\n[bold red]Terminating {len(instances_to_terminate)} instances across {len(by_region)} regions...[/bold red]")
        
        terminate_threads = []
        start_time = time.time()
        
        for region, ids in by_region.items():
            thread = threading.Thread(target=terminate_region_instances, args=(region, ids))
            thread.daemon = True
            terminate_threads.append(thread)
            thread.start()
        
        # Show spinner while waiting
        with console.status("[red]Terminating instances...[/red]", spinner="dots"):
            for thread in terminate_threads:
                thread.join(timeout=60)  # 60 second timeout per region
        
        terminate_time = time.time() - start_time
        
        # Show results
        for region, count, status, error in termination_results:
            if status == "success":
                rich_success(f"Terminated {count} instances in {region}")
            else:
                rich_error(f"Failed to terminate {count} instances in {region}: {error}")
                
        console.print(f"[green]✓ Completed termination in {terminate_time:.1f} seconds[/green]")
    else:
        # Fallback without fancy display
        terminate_threads = []
        for region, ids in by_region.items():
            thread = threading.Thread(target=terminate_region_instances, args=(region, ids))
            thread.daemon = True
            terminate_threads.append(thread)
            thread.start()
        
        for thread in terminate_threads:
            thread.join(timeout=60)
            
        # Show results
        for region, count, status, error in termination_results:
            if status == "success":
                rich_success(f"Terminated {count} instances in {region}")
            else:
                rich_error(f"Failed to terminate {count} instances in {region}: {error}")

    rich_success(
        f"✅ Nuke complete. Terminated {total_terminated} instances across {len(by_region)} regions."
    )

    # Clean up local state file
    state.save_instances([])
    rich_success("✅ Cleared local instance state file (instances.json).")

    # Comprehensive cleanup
    rich_status("🧹 Running comprehensive resource cleanup...")
    _cleanup_vpcs()

    # Final verification
    rich_success("🎯 Nuke operation completed successfully!")
    rich_status("💡 Tip: Run 'list' command to verify local state is now empty.")
    rich_status(
        "💡 Tip: Check AWS console to confirm all tagged resources are terminated."
    )


def _cleanup_vpcs() -> None:
    """Clean up VPCs and other resources created by this tool."""
    rich_status("Cleaning up VPCs and other resources...")

    # Get regions from config
    config = SimpleConfig()
    regions = config.regions()

    if not regions:
        rich_warning("No regions configured for cleanup")
        return

    if RICH_AVAILABLE and console:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            total_cleaned = 0
            for region in regions:
                task = progress.add_task(f"Scanning VPCs in {region}...", total=None)
                try:
                    ec2 = boto3.client("ec2", region_name=region)

                    # Find VPCs with SpotDeployer tags
                    vpcs = ec2.describe_vpcs(
                        Filters=[
                            {"Name": "tag:ManagedBy", "Values": ["SpotDeployer"]},
                        ]
                    )

                    for vpc in vpcs["Vpcs"]:
                        vpc_id = vpc["VpcId"]
                        progress.update(
                            task, description=f"Cleaning VPC {vpc_id} in {region}..."
                        )
                        try:
                            # Check if VPC has any instances
                            instances = ec2.describe_instances(
                                Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
                            )

                            has_running_instances = any(
                                instance["State"]["Name"]
                                not in ["terminated", "shutting-down"]
                                for reservation in instances["Reservations"]
                                for instance in reservation["Instances"]
                            )

                            if has_running_instances:
                                progress.remove_task(task)
                                rich_warning(
                                    f"VPC {vpc_id} in {region} has running instances, skipping"
                                )
                                task = progress.add_task(
                                    f"Scanning VPCs in {region}...", total=None
                                )
                                continue

                            # Try basic cleanup
                            # Delete security groups (except default)
                            sgs = ec2.describe_security_groups(
                                Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
                            )
                            for sg in sgs["SecurityGroups"]:
                                if sg["GroupName"] != "default":
                                    try:
                                        ec2.delete_security_group(GroupId=sg["GroupId"])
                                    except Exception:
                                        pass  # May fail due to dependencies

                            # Delete subnets
                            subnets = ec2.describe_subnets(
                                Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
                            )
                            for subnet in subnets["Subnets"]:
                                try:
                                    ec2.delete_subnet(SubnetId=subnet["SubnetId"])
                                except Exception:
                                    pass  # May fail due to dependencies

                            # Try to delete VPC
                            try:
                                ec2.delete_vpc(VpcId=vpc_id)
                                progress.remove_task(task)
                                rich_success(f"Cleaned up VPC {vpc_id} in {region}")
                                total_cleaned += 1
                                task = progress.add_task(
                                    f"Scanning VPCs in {region}...", total=None
                                )
                            except Exception as e:
                                progress.remove_task(task)
                                rich_warning(
                                    f"Could not fully delete VPC {vpc_id}: {e}"
                                )
                                rich_status(
                                    "For comprehensive cleanup, use: uv run -s delete_vpcs.py"
                                )
                                task = progress.add_task(
                                    f"Scanning VPCs in {region}...", total=None
                                )

                        except Exception as e:
                            progress.remove_task(task)
                            rich_warning(f"Error processing VPC {vpc_id}: {e}")
                            task = progress.add_task(
                                f"Scanning VPCs in {region}...", total=None
                            )

                    progress.remove_task(task)

                except Exception as e:
                    progress.remove_task(task)
                    rich_warning(f"Error cleaning up region {region}: {e}")
    else:
        # Fallback without progress bar
        total_cleaned = 0
        for region in regions:
            try:
                ec2 = boto3.client("ec2", region_name=region)

                # Find VPCs with SpotDeployer tags
                vpcs = ec2.describe_vpcs(
                    Filters=[
                        {"Name": "tag:ManagedBy", "Values": ["SpotDeployer"]},
                    ]
                )

                for vpc in vpcs["Vpcs"]:
                    vpc_id = vpc["VpcId"]
                    try:
                        # Check if VPC has any instances
                        instances = ec2.describe_instances(
                            Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
                        )

                        has_running_instances = any(
                            instance["State"]["Name"]
                            not in ["terminated", "shutting-down"]
                            for reservation in instances["Reservations"]
                            for instance in reservation["Instances"]
                        )

                        if has_running_instances:
                            rich_warning(
                                f"VPC {vpc_id} in {region} has running instances, skipping"
                            )
                            continue

                        # Try basic cleanup
                        rich_status(f"Cleaning up VPC {vpc_id} in {region}...")

                        # Delete security groups (except default)
                        sgs = ec2.describe_security_groups(
                            Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
                        )
                        for sg in sgs["SecurityGroups"]:
                            if sg["GroupName"] != "default":
                                try:
                                    ec2.delete_security_group(GroupId=sg["GroupId"])
                                except Exception:
                                    pass  # May fail due to dependencies

                        # Delete subnets
                        subnets = ec2.describe_subnets(
                            Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
                        )
                        for subnet in subnets["Subnets"]:
                            try:
                                ec2.delete_subnet(SubnetId=subnet["SubnetId"])
                            except Exception:
                                pass  # May fail due to dependencies

                        # Try to delete VPC
                        try:
                            ec2.delete_vpc(VpcId=vpc_id)
                            rich_success(f"Cleaned up VPC {vpc_id} in {region}")
                            total_cleaned += 1
                        except Exception as e:
                            rich_warning(f"Could not fully delete VPC {vpc_id}: {e}")
                            rich_status(
                                "For comprehensive cleanup, use: uv run -s delete_vpcs.py"
                            )

                    except Exception as e:
                        rich_warning(f"Error processing VPC {vpc_id}: {e}")

            except Exception as e:
                rich_warning(f"Error cleaning up region {region}: {e}")

    if total_cleaned > 0:
        rich_success(f"Cleaned up {total_cleaned} VPCs")
    else:
        rich_status("No VPCs needed cleanup")


def cmd_setup() -> None:
    """Setup enhanced configuration."""
    rich_status("Setting up enhanced configuration...")

    if not check_aws_auth():
        return

    config_data = {
        "aws": {
            "username": "ubuntu",
            "files_directory": "files",
            "scripts_directory": "instance/scripts",
            "cloud_init_template": "instance/cloud-init/init-vm-template.yml",
            "startup_script": "instance/scripts/startup.py",
            "bacalhau_data_dir": "/bacalhau_data",
            "bacalhau_node_dir": "/bacalhau_node",
            "bacalhau_config_template": "instance/config/config-template.yaml",
            "docker_compose_template": "instance/scripts/docker-compose.yaml",
            "instance_storage_gb": 20,
            "associate_public_ip": True,
            "tags": {
                "Project": "SpotDeployment",
                "Environment": "Development",
                "ManagedBy": "SpotDeployer",
            },
        },
        "regions": [
            {
                "us-west-2": {
                    "machine_type": "t3.medium",
                    "image": "auto",
                    "instances_per_region": 1,
                }
            },
            {
                "us-east-1": {
                    "machine_type": "t3.medium",
                    "image": "auto",
                    "instances_per_region": 1,
                }
            },
            {
                "eu-west-1": {
                    "machine_type": "t3.medium",
                    "image": "auto",
                    "instances_per_region": 1,
                }
            },
        ],
    }

    # Check for existing SSH keys
    home_dir = os.path.expanduser("~")
    ssh_dir = os.path.join(home_dir, ".ssh")
    common_keys = ["id_rsa", "id_ed25519"]
    found_key = False

    for key in common_keys:
        private_key_path = os.path.join(ssh_dir, key)
        public_key_path = f"{private_key_path}.pub"
        if os.path.exists(private_key_path) and os.path.exists(public_key_path):
            config_data["aws"]["private_ssh_key_path"] = f"~/.ssh/{key}"
            config_data["aws"]["public_ssh_key_path"] = f"~/.ssh/{key}.pub"
            rich_status(f"Found existing SSH key: ~/.ssh/{key}")
            found_key = True
            break

    if not found_key:
        rich_warning("No common SSH keys found. You may need to generate one.")

    with open("config.yaml", "w") as f:
        yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

    rich_success("Enhanced config.yaml created successfully!")
    rich_status("Review and edit config.yaml as needed.")


def cmd_node_config() -> None:
    """Generate sample configuration for N nodes."""
    if len(sys.argv) < 3:
        rich_error("Usage: uv run -s deploy_spot.py node-config <number_of_nodes>")
        rich_status("Example: uv run -s deploy_spot.py node-config 50")
        return

    try:
        num_nodes = int(sys.argv[2])
        if num_nodes <= 0:
            rich_error("Number of nodes must be positive")
            return
    except ValueError:
        rich_error("Number of nodes must be a valid integer")
        return

    rich_status(f"Generating configuration for {num_nodes} nodes...")

    # Available regions with machine types
    available_regions = [
        {"us-west-2": {"machine_type": "t3.medium", "image": "auto"}},
        {"us-east-1": {"machine_type": "t3.medium", "image": "auto"}},
        {"eu-west-1": {"machine_type": "t3.medium", "image": "auto"}},
        {"us-west-1": {"machine_type": "t3.medium", "image": "auto"}},
        {"eu-central-1": {"machine_type": "t3.medium", "image": "auto"}},
        {"ap-southeast-1": {"machine_type": "t3.medium", "image": "auto"}},
        {"ap-northeast-1": {"machine_type": "t3.medium", "image": "auto"}},
        {"eu-north-1": {"machine_type": "t3.medium", "image": "auto"}},
        {"ca-central-1": {"machine_type": "t3.medium", "image": "auto"}},
        {"ap-south-1": {"machine_type": "t3.medium", "image": "auto"}},
    ]

    # Calculate how many regions we need (3 nodes per region max)
    max_nodes_per_region = 3
    regions_needed = min(
        len(available_regions),
        (num_nodes + max_nodes_per_region - 1) // max_nodes_per_region,
    )

    # Randomly select regions
    import random

    random.seed(42)  # For reproducible results
    selected_regions = random.sample(available_regions, regions_needed)

    # Distribute nodes across regions
    nodes_per_region = num_nodes // regions_needed
    remaining_nodes = num_nodes % regions_needed

    region_distribution = []
    for i, region_config in enumerate(selected_regions):
        nodes_in_region = nodes_per_region
        if i < remaining_nodes:
            nodes_in_region += 1
        region_distribution.append((region_config, nodes_in_region))

    # Generate configuration
    config_data = {
        "aws": {
            "username": "ubuntu",
            "ssh_key_name": "your-key-name",
            "public_ssh_key_path": "~/.ssh/id_rsa.pub",
            "private_ssh_key_path": "~/.ssh/id_rsa",
            "files_directory": "files",
            "scripts_directory": "instance/scripts",
            "startup_script": "instance/scripts/startup.py",
            "bacalhau_data_dir": "/bacalhau_data",
            "bacalhau_node_dir": "/bacalhau_node",
            "bacalhau_config_template": "instance/config/config-template.yaml",
            "docker_compose_template": "instance/scripts/docker-compose.yaml",
            "instance_storage_gb": 20,
            "associate_public_ip": True,
            "tags": {
                "Project": "SpotDeployment",
                "Environment": "Development",
                "ManagedBy": "SpotDeployer",
                "NodeCount": str(num_nodes),
            },
        },
        "regions": [],
    }

    # Add regions with their node counts
    for region_config, node_count in region_distribution:
        region_name = list(region_config.keys())[0]
        region_config[region_name]["instances_per_region"] = node_count
        config_data["regions"].append(region_config)

    # Display distribution
    rich_status("Node distribution across regions:")
    for region_config, node_count in region_distribution:
        region_name = list(region_config.keys())[0]
        rich_status(f"  {region_name}: {node_count} nodes")

    # Write configuration file
    config_filename = f"config-{num_nodes}nodes.yaml"
    try:
        with open(config_filename, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

        rich_success(f"Generated {config_filename} for {num_nodes} nodes")
        rich_status(f"To use: cp {config_filename} config.yaml")
        rich_status("Then run: uv run -s deploy_spot.py create")
    except Exception as e:
        rich_error(f"Failed to write config file: {e}")


def print_help() -> None:
    """Show help information."""
    if RICH_AVAILABLE and console:
        # Create beautiful Rich panel
        help_content = """[bold cyan]Commands:[/bold cyan]
  [bold green]setup[/bold green]           Create basic configuration
  [bold green]node-config[/bold green]     Generate sample configuration for N nodes
  [bold green]create[/bold green]          Create spot instances in configured regions
  [bold green]list[/bold green]            List all managed instances
  [bold yellow]random-instance[/bold yellow]  Get SSH command for a random instance
  [bold yellow]print-log[/bold yellow]       Print startup log from a random instance
  [bold yellow]debug-log[/bold yellow]       Print comprehensive debug info from a random instance
  [bold green]destroy[/bold green]         Terminate instances and clean up ALL resources
  [bold red]nuke[/bold red]            Force terminate ALL tagged instances (queries AWS directly)
  [bold green]help[/bold green]            Show this help

[bold cyan]Examples:[/bold cyan]
  [dim]uv run -s deploy_spot.py setup         # First time setup[/dim]
  [dim]uv run -s deploy_spot.py node-config 5 # Generate config for 5 nodes[/dim]
  [dim]uv run -s deploy_spot.py create        # Deploy instances[/dim]
  [dim]uv run -s deploy_spot.py list          # Check status[/dim]
  [dim]uv run -s deploy_spot.py random-instance # Get a random instance[/dim]
  [dim]uv run -s deploy_spot.py print-log     # View startup log[/dim]
  [dim]uv run -s deploy_spot.py debug-log     # Full debug info[/dim]
  [dim]uv run -s deploy_spot.py destroy       # Cleanup everything[/dim]
  [dim]uv run -s deploy_spot.py nuke          # Force cleanup from AWS API[/dim]

[bold cyan]Files:[/bold cyan]
  [yellow]config.yaml[/yellow]     Configuration file (created by 'setup' command)
  [yellow]instances.json[/yellow]  State file (tracks your instances)
  [yellow]delete_vpcs.py[/yellow]  Advanced VPC cleanup utility

[bold cyan]Advanced:[/bold cyan]
  [dim]uv run -s delete_vpcs.py --dry-run    # Comprehensive VPC scan[/dim]
  [dim]uv run -s delete_vpcs.py              # Advanced VPC cleanup[/dim]"""

        panel = Panel(
            help_content,
            title="[bold white]AWS Spot Instance Deployer - Simple Version[/bold white]",
            border_style="blue",
        )
        console.print(panel)
    else:
        # Fallback to simple text
        print(
            """
AWS Spot Instance Deployer

Commands:
  setup           Create basic configuration
  node-config     Generate sample configuration for N nodes
  create          Create spot instances in configured regions
  list            List all managed instances
  random-instance Get SSH command for a random instance
  print-log       Print startup log from a random instance
  debug-log       Print comprehensive debug info from a random instance
  destroy         Terminate instances and clean up ALL resources
  nuke            Force terminate ALL tagged instances (queries AWS directly)
  help            Show this help

Examples:
  uv run -s deploy_spot.py setup         # First time setup
  uv run -s deploy_spot.py node-config 5 # Generate config for 5 nodes
  uv run -s deploy_spot.py create        # Deploy instances
  uv run -s deploy_spot.py list          # Check status
  uv run -s deploy_spot.py random-instance # Get a random instance
  uv run -s deploy_spot.py print-log     # View startup log
  uv run -s deploy_spot.py debug-log     # Full debug info
  uv run -s deploy_spot.py destroy       # Cleanup everything
  uv run -s deploy_spot.py nuke          # Force cleanup from AWS API

Files:
  config.yaml     Configuration file (created by 'setup' command)
  instances.json  State file (tracks your instances)
  delete_vpcs.py  Advanced VPC cleanup utility
  
Advanced:
  uv run -s delete_vpcs.py --dry-run    # Comprehensive VPC scan
  uv run -s delete_vpcs.py              # Advanced VPC cleanup
"""
        )


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


def main():
    """Main entry point."""
    if len(sys.argv) == 1 or sys.argv[1] in ["-h", "--help", "help"]:
        print_help()
        return

    command = sys.argv[1]
    config = SimpleConfig()
    state = SimpleStateManager()

    if command == "setup":
        cmd_setup()
    elif command == "create":
        cmd_create(config, state)
    elif command == "list":
        cmd_list(state)
    elif command == "random-instance":
        cmd_random_instance(state, config)
    elif command == "print-log":
        cmd_print_log(state, config)
    elif command == "debug-log":
        cmd_debug_log(state, config)
    elif command == "destroy":
        cmd_destroy(state)
    elif command == "nuke":
        cmd_nuke(state)
    elif command == "node-config":
        cmd_node_config()
    else:
        rich_error(f"Unknown command: {command}")
        print_help()


def show_help():
    """Alias for print_help for backwards compatibility."""
    print_help()


if __name__ == "__main__":
    main()
