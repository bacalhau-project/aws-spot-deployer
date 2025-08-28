#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "pyyaml",
#   "rich",
# ]
# ///
"""
SkyPilot Cluster Manager - Python implementation of cluster operations.

This replaces the fragile bash script logic with proper Python tooling for:
- YAML parsing instead of grep/sed
- Structured logging with rich
- Better error handling
- Docker container management
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml
from rich.console import Console
from rich.table import Table


class ClusterManager:
    """Manages SkyPilot cluster operations through Docker container."""

    def __init__(
        self, log_to_console: bool = False, log_file: str = "cluster-deploy.log"
    ):
        self.console = Console()
        self.log_to_console = log_to_console
        self.log_file = Path(log_file)
        self.docker_container = "skypilot-cluster-deploy"
        self.skypilot_image = "berkeleyskypilot/skypilot"

    def log(self, level: str, message: str, style: str = ""):
        """Log message to console and/or file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if self.log_to_console:
            self.console.print(f"[{level}] {message}", style=style)
        else:
            # Write to file
            with open(self.log_file, "a") as f:
                f.write(f"[{timestamp}] [{level}] {message}\n")
            # Also show brief status to console
            self.console.print(f"[{level}] {message}", style=style)

    def log_info(self, message: str):
        self.log("INFO", message, "blue")

    def log_success(self, message: str):
        self.log("SUCCESS", message, "green")

    def log_warning(self, message: str):
        self.log("WARNING", message, "yellow")

    def log_error(self, message: str):
        self.log("ERROR", message, "red")

    def log_header(self, message: str):
        if self.log_to_console:
            self.console.print(f"\n🌍 {message}", style="bold blue")
            self.console.print()
        else:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.log_file, "a") as f:
                f.write(f"\n[{timestamp}] [HEADER] 🌍 {message}\n\n")
            self.console.print(f"\n🌍 {message}", style="bold blue")
            self.console.print()

    def load_cluster_config(self, config_file: str = "cluster.yaml") -> dict:
        """Load and parse cluster configuration from YAML."""
        try:
            with open(config_file) as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.log_error(f"Failed to load config {config_file}: {e}")
            sys.exit(1)

    def get_cluster_name_from_config(self, config_file: str = "cluster.yaml") -> str:
        """Extract cluster name from YAML config."""
        config = self.load_cluster_config(config_file)
        return config.get("name", "cluster")

    def ensure_docker_container(self) -> bool:
        """Ensure Docker container is running."""
        # Check if container is already running
        result = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                f"name={self.docker_container}",
                "--filter",
                "status=running",
                "--quiet",
            ],
            capture_output=True,
            text=True,
        )

        if result.stdout.strip():
            return True  # Container already running

        self.log_info("Starting SkyPilot Docker container...")

        # Remove any existing stopped container
        subprocess.run(
            ["docker", "rm", self.docker_container],
            capture_output=True,
            stderr=subprocess.DEVNULL,
        )

        # Start new container
        home = os.path.expanduser("~")
        cwd = os.getcwd()

        cmd = [
            "docker",
            "run",
            "-td",
            "--rm",
            "--name",
            self.docker_container,
            "-v",
            f"{home}/.sky:/root/.sky:rw",
            "-v",
            f"{home}/.aws:/root/.aws:rw",
            "-v",
            f"{home}/.config/gcloud:/root/.config/gcloud:rw",
            "-v",
            f"{cwd}:/workspace:rw",
            "-w",
            "/workspace",
            self.skypilot_image,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            self.log_success("SkyPilot Docker container started")
            return True
        else:
            self.log_error("Failed to start SkyPilot Docker container")
            return False

    def run_sky_cmd(self, *args) -> tuple[bool, str, str]:
        """Run sky command in Docker container. Returns (success, stdout, stderr)."""
        if not self.ensure_docker_container():
            return False, "", "Failed to start container"

        cmd = ["docker", "exec", self.docker_container, "sky"] + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr

    def get_sky_cluster_name(self) -> Optional[str]:
        """Get actual SkyPilot cluster name from status."""
        success, stdout, stderr = self.run_sky_cmd("status", "--format", "json")
        if success and stdout.strip():
            try:
                data = json.loads(stdout)
                clusters = data.get("clusters", [])
                if clusters:
                    return clusters[0].get("name")
            except json.JSONDecodeError:
                pass

        # Fallback to text parsing
        success, stdout, stderr = self.run_sky_cmd("status")
        if success:
            for line in stdout.split("\n"):
                line = line.strip()
                if (
                    line
                    and not line.startswith("NAME")
                    and not line.startswith("Enabled")
                ):
                    parts = line.split()
                    if parts and parts[0].startswith("sky-"):
                        return parts[0]

        return None

    def check_prerequisites(self) -> bool:
        """Check Docker and SkyPilot availability."""
        self.log_header("Checking Prerequisites")

        # Check Docker
        try:
            subprocess.run(["docker", "--version"], capture_output=True, check=True)
            subprocess.run(["docker", "info"], capture_output=True, check=True)
            self.log_success("Docker is available and running")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.log_error("Docker not found or not running")
            return False

        # Check SkyPilot image
        self.log_info("Ensuring SkyPilot Docker image is available...")
        result = subprocess.run(
            ["docker", "image", "inspect", self.skypilot_image], capture_output=True
        )

        if result.returncode != 0:
            self.log_info("Pulling SkyPilot Docker image...")
            result = subprocess.run(["docker", "pull", self.skypilot_image])
            if result.returncode != 0:
                self.log_error("Failed to pull SkyPilot Docker image")
                return False

        # Test SkyPilot
        success, stdout, stderr = self.run_sky_cmd("--version")
        if not success:
            self.log_error("SkyPilot not available in Docker container")
            return False

        version = stdout.split("\n")[0] if stdout else "unknown"
        self.log_success(f"SkyPilot available: {version}")

        # Check AWS credentials
        if Path("~/.aws/credentials").expanduser().exists() or os.getenv(
            "AWS_ACCESS_KEY_ID"
        ):
            success, stdout, stderr = self.run_sky_cmd("check")
            if success and "AWS: enabled" in stdout:
                try:
                    result = subprocess.run(
                        [
                            "aws",
                            "sts",
                            "get-caller-identity",
                            "--query",
                            "Account",
                            "--output",
                            "text",
                        ],
                        capture_output=True,
                        text=True,
                    )
                    account = (
                        result.stdout.strip() if result.returncode == 0 else "unknown"
                    )
                    self.log_success(f"AWS credentials available (Account: {account})")
                except FileNotFoundError:
                    self.log_warning(
                        "AWS credentials configured but aws CLI not available"
                    )
            else:
                self.log_warning(
                    "AWS credentials configured but not working with SkyPilot"
                )
        else:
            self.log_warning("AWS credentials not found")

        return True

    def deploy_cluster(self, config_file: str = "cluster.yaml") -> bool:
        """Deploy cluster using SkyPilot."""
        if not Path(config_file).exists():
            self.log_error(f"Config file not found: {config_file}")
            return False

        cluster_name = self.get_cluster_name_from_config(config_file)
        deployment_id = f"cluster-deploy-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        self.log_header(f"Deploying Global Cluster: {cluster_name}")
        self.log_info(f"Using config: {config_file}")
        self.log_info(f"Cluster name: {cluster_name}")
        self.log_info(f"Deployment ID: {deployment_id}")

        # Set environment variable for deployment ID
        os.environ["CLUSTER_DEPLOYMENT_ID"] = deployment_id

        self.log_info("Launching cluster (this may take 5-10 minutes)...")

        # Launch cluster
        if self.log_to_console:
            # Show output when -f flag used
            success, stdout, stderr = self.run_sky_cmd(
                "launch", config_file, "--name", cluster_name, "--yes"
            )
            if stdout:
                print(stdout)
            if stderr:
                print(stderr, file=sys.stderr)
        else:
            # Redirect to log file
            self.console.print(
                f"Deploying cluster... (check {self.log_file} for detailed progress)"
            )
            success, stdout, stderr = self.run_sky_cmd(
                "launch", config_file, "--name", cluster_name, "--yes"
            )
            with open(self.log_file, "a") as f:
                if stdout:
                    f.write(stdout + "\n")
                if stderr:
                    f.write(stderr + "\n")

        if success:
            self.log_success(f"Cluster '{cluster_name}' deployed successfully!")
            self._show_completion_banner()
            return True
        else:
            self.log_error("Deployment failed")
            return False

    def _show_completion_banner(self):
        """Show deployment completion banner."""
        self.console.print()
        self.console.print(
            "┌─────────────────────────────────────────────────┐", style="green"
        )
        self.console.print(
            "│               🎉 Deployment Complete            │", style="green"
        )
        self.console.print(
            "├─────────────────────────────────────────────────┤", style="green"
        )
        self.console.print(
            "│ Next Steps:                                     │", style="green"
        )
        self.console.print(
            "│ • Check status: ./cluster-deploy status        │", style="green"
        )
        self.console.print(
            "│ • List nodes: ./cluster-deploy list            │", style="green"
        )
        self.console.print(
            "│ • SSH to cluster: ./cluster-deploy ssh         │", style="green"
        )
        self.console.print(
            "│ • View logs: ./cluster-deploy logs             │", style="green"
        )
        self.console.print(
            "│ • Destroy cluster: ./cluster-deploy destroy    │", style="green"
        )
        self.console.print(
            "└─────────────────────────────────────────────────┘", style="green"
        )
        self.console.print()

    def show_status(self) -> bool:
        """Show cluster status."""
        self.log_header("Cluster Status")
        success, stdout, stderr = self.run_sky_cmd("status")
        if success:
            print(stdout)
            return True
        else:
            self.log_error("Failed to get cluster status")
            if stderr:
                print(stderr, file=sys.stderr)
            return False

    def list_nodes(self) -> bool:
        """Show detailed node information in a table."""
        cluster_name = self.get_sky_cluster_name()
        if not cluster_name:
            self.log_error("No running cluster found")
            return False

        self.log_header(f"Cluster Nodes: {cluster_name}")

        # Get cluster info
        success, stdout, stderr = self.run_sky_cmd("status", "--name", cluster_name)
        if not success:
            self.log_error("Failed to get cluster information")
            return False

        # Parse launch time
        launch_time = "unknown"
        for line in stdout.split("\n"):
            if cluster_name in line:
                parts = line.split()
                if len(parts) >= 8:
                    launch_time = " ".join(parts[5:8])
                break

        # Get number of nodes from config
        config = self.load_cluster_config()
        num_nodes = config.get("num_nodes", 9)

        # Create table
        table = Table(title=f"Cluster: {cluster_name}")
        table.add_column("Node", style="cyan")
        table.add_column("Instance ID", style="magenta")
        table.add_column("Public IP", style="green")
        table.add_column("Zone", style="yellow")
        table.add_column("Launched", style="blue")

        # Add rows (basic info since we can't easily query each node individually)
        for i in range(num_nodes):
            table.add_row(
                f"node-{i}", "querying...", "querying...", "various", launch_time
            )

        self.console.print(table)
        self.console.print(f"\n[green]Total nodes: {num_nodes}[/green]")
        self.console.print("[green]Cluster status: UP[/green]")

        return True

    def ssh_cluster(self) -> bool:
        """SSH to cluster head node."""
        cluster_name = self.get_sky_cluster_name()
        if not cluster_name:
            self.log_error("No running cluster found")
            return False

        self.log_info(f"Connecting to head node of cluster: {cluster_name}")

        # Use interactive docker exec to SSH
        cmd = ["docker", "exec", "-it", self.docker_container, "ssh", cluster_name]
        result = subprocess.run(cmd)
        return result.returncode == 0

    def show_logs(self) -> bool:
        """Show cluster logs."""
        cluster_name = self.get_sky_cluster_name()
        if not cluster_name:
            self.log_error("No running cluster found")
            return False

        self.log_info(f"Showing logs for cluster: {cluster_name}")
        success, stdout, stderr = self.run_sky_cmd("logs", cluster_name)
        if success:
            print(stdout)
            return True
        else:
            self.log_error("Failed to get cluster logs")
            if stderr:
                print(stderr, file=sys.stderr)
            return False

    def destroy_cluster(self) -> bool:
        """Destroy the cluster."""
        cluster_name = self.get_sky_cluster_name()
        if not cluster_name:
            self.log_info("No running cluster found to destroy")
            return True

        self.log_header(f"Destroying Cluster: {cluster_name}")
        self.log_warning("This will terminate all instances and delete all data!")

        success, stdout, stderr = self.run_sky_cmd("down", cluster_name, "--yes")
        if success:
            if "not found" in stdout:
                self.log_info(f"Cluster '{cluster_name}' does not exist")
            else:
                self.log_success(f"Cluster '{cluster_name}' destroyed")
            return True
        else:
            self.log_error("Failed to destroy cluster")
            if stderr:
                print(stderr, file=sys.stderr)
            return False

    def cleanup_docker(self) -> bool:
        """Clean up Docker container."""
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={self.docker_container}", "--quiet"],
            capture_output=True,
        )

        if result.stdout.strip():
            self.log_info("Stopping SkyPilot Docker container...")
            subprocess.run(
                ["docker", "stop", self.docker_container], capture_output=True
            )
            self.log_success("Docker container stopped")

        return True


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="SkyPilot Cluster Manager")
    parser.add_argument(
        "command",
        choices=[
            "create",
            "destroy",
            "status",
            "list",
            "ssh",
            "logs",
            "cleanup",
            "check",
        ],
    )
    parser.add_argument("-c", "--config", default="cluster.yaml", help="Config file")
    parser.add_argument("-f", "--console", action="store_true", help="Log to console")
    parser.add_argument(
        "--log-file", default="cluster-deploy.log", help="Log file path"
    )

    args = parser.parse_args()

    manager = ClusterManager(log_to_console=args.console, log_file=args.log_file)

    if args.command == "create":
        if not manager.check_prerequisites():
            sys.exit(1)
        if not manager.deploy_cluster(args.config):
            sys.exit(1)
    elif args.command == "destroy":
        if not manager.destroy_cluster():
            sys.exit(1)
    elif args.command == "status":
        if not manager.check_prerequisites():
            sys.exit(1)
        if not manager.show_status():
            sys.exit(1)
    elif args.command == "list":
        if not manager.check_prerequisites():
            sys.exit(1)
        if not manager.list_nodes():
            sys.exit(1)
    elif args.command == "ssh":
        if not manager.check_prerequisites():
            sys.exit(1)
        if not manager.ssh_cluster():
            sys.exit(1)
    elif args.command == "logs":
        if not manager.check_prerequisites():
            sys.exit(1)
        if not manager.show_logs():
            sys.exit(1)
    elif args.command == "cleanup":
        manager.cleanup_docker()
    elif args.command == "check":
        if not manager.check_prerequisites():
            sys.exit(1)


if __name__ == "__main__":
    main()
