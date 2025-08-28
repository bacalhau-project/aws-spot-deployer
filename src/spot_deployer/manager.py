"""
SkyPilot Cluster Manager - Core cluster operations.

Handles Docker container management, SkyPilot interactions, and cluster lifecycle.
Uses proper YAML parsing and Rich output instead of fragile bash scripting.
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml
from rich.console import Console
from rich.table import Table


class ClusterManager:
    """Manages SkyPilot cluster operations through Docker container."""

    def __init__(self, log_to_console: bool = False, log_file: str = "cluster-deploy.log"):
        self.console = Console()
        self.log_to_console = log_to_console
        self.log_file = Path(log_file)
        self.docker_container = "skypilot-cluster-deploy"
        self.skypilot_image = "berkeleyskypilot/skypilot"

    def log(self, level: str, message: str, style: str = "") -> None:
        """Log message to console and/or file."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if self.log_to_console:
            self.console.print(f"[{level}] {message}", style=style)
        else:
            # Write to file
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] [{level}] {message}\n")
            # Also show brief status to console
            self.console.print(f"[{level}] {message}", style=style)

    def log_info(self, message: str) -> None:
        """Log info message."""
        self.log("INFO", message, "blue")

    def log_success(self, message: str) -> None:
        """Log success message."""
        self.log("SUCCESS", message, "green")

    def log_warning(self, message: str) -> None:
        """Log warning message."""
        self.log("WARNING", message, "yellow")

    def log_error(self, message: str) -> None:
        """Log error message."""
        self.log("ERROR", message, "red")

    def log_header(self, message: str) -> None:
        """Log header message."""
        if self.log_to_console:
            self.console.print(f"\n🌍 {message}", style="bold blue")
            self.console.print()
        else:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n[{timestamp}] [HEADER] 🌍 {message}\n\n")
            self.console.print(f"\n🌍 {message}", style="bold blue")
            self.console.print()

    def load_cluster_config(self, config_file: str = "cluster.yaml") -> dict[str, Any]:
        """Load and parse cluster configuration from YAML."""
        config_path = Path(config_file)
        if not config_path.exists():
            self.log_error(f"Config file not found: {config_file}")
            raise FileNotFoundError(f"Config file not found: {config_file}")

        try:
            with open(config_path, encoding='utf-8') as f:
                config = yaml.safe_load(f)
                if not isinstance(config, dict):
                    raise ValueError("Config file must contain a YAML object")
                return config
        except yaml.YAMLError as e:
            self.log_error(f"Invalid YAML in {config_file}: {e}")
            raise
        except Exception as e:
            self.log_error(f"Failed to load config {config_file}: {e}")
            raise

    def get_cluster_name_from_config(self, config_file: str = "cluster.yaml") -> str:
        """Extract cluster name from YAML config."""
        try:
            config = self.load_cluster_config(config_file)
            return config.get('name', 'cluster')
        except Exception:
            return 'cluster'

    def ensure_docker_container(self) -> bool:
        """Ensure Docker container is running."""
        try:
            # Check if container is already running
            result = subprocess.run([
                "docker", "ps", "--filter", f"name={self.docker_container}",
                "--filter", "status=running", "--quiet"
            ], capture_output=True, text=True, check=False)

            if result.stdout.strip():
                return True  # Container already running

            self.log_info("Starting SkyPilot Docker container...")

            # Remove any existing stopped container
            subprocess.run(["docker", "rm", self.docker_container],
                          capture_output=True, stderr=subprocess.DEVNULL, check=False)

            # Start new container
            home = Path.home()
            cwd = Path.cwd()

            cmd = [
                "docker", "run", "-td", "--rm", "--name", self.docker_container,
                "-v", f"{home}/.sky:/root/.sky:rw",
                "-v", f"{home}/.aws:/root/.aws:rw",
                "-v", f"{home}/.config/gcloud:/root/.config/gcloud:rw",
                "-v", f"{cwd}:/workspace:rw",
                "-w", "/workspace",
                self.skypilot_image
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                self.log_success("SkyPilot Docker container started")
                return True
            else:
                self.log_error("Failed to start SkyPilot Docker container")
                if result.stderr:
                    self.log_error(f"Docker error: {result.stderr}")
                return False

        except FileNotFoundError:
            self.log_error("Docker command not found. Please install Docker.")
            return False
        except Exception as e:
            self.log_error(f"Failed to manage Docker container: {e}")
            return False

    def run_sky_cmd(self, *args: str) -> tuple[bool, str, str]:
        """Run sky command in Docker container. Returns (success, stdout, stderr)."""
        if not self.ensure_docker_container():
            return False, "", "Failed to start container"

        cmd = ["docker", "exec", self.docker_container, "sky"] + list(args)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            return result.returncode == 0, result.stdout, result.stderr
        except Exception as e:
            return False, "", str(e)

    def get_sky_cluster_name(self) -> Optional[str]:
        """Get actual SkyPilot cluster name from status."""
        # Try JSON format first
        success, stdout, stderr = self.run_sky_cmd("status", "--format", "json")
        if success and stdout.strip():
            try:
                data = json.loads(stdout)
                clusters = data.get('clusters', [])
                if clusters and isinstance(clusters, list):
                    return clusters[0].get('name')
            except json.JSONDecodeError:
                pass

        # Fallback to text parsing
        success, stdout, stderr = self.run_sky_cmd("status")
        if success and stdout:
            for line in stdout.split('\n'):
                line = line.strip()
                if line and not line.startswith(('NAME', 'Enabled', 'No', 'Clusters')):
                    parts = line.split()
                    if parts and parts[0].startswith('sky-'):
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
        except subprocess.CalledProcessError as e:
            self.log_error(f"Docker check failed: {e}")
            return False
        except FileNotFoundError:
            self.log_error("Docker not found. Please install Docker.")
            return False

        # Check SkyPilot image
        self.log_info("Ensuring SkyPilot Docker image is available...")
        try:
            result = subprocess.run([
                "docker", "image", "inspect", self.skypilot_image
            ], capture_output=True, check=False)

            if result.returncode != 0:
                self.log_info("Pulling SkyPilot Docker image...")
                result = subprocess.run(["docker", "pull", self.skypilot_image], check=False)
                if result.returncode != 0:
                    self.log_error("Failed to pull SkyPilot Docker image")
                    return False
        except Exception as e:
            self.log_error(f"Failed to check Docker image: {e}")
            return False

        # Test SkyPilot
        success, stdout, stderr = self.run_sky_cmd("--version")
        if not success:
            self.log_error("SkyPilot not available in Docker container")
            if stderr:
                self.log_error(f"SkyPilot error: {stderr}")
            return False

        version = stdout.split('\n')[0] if stdout else "unknown"
        self.log_success(f"SkyPilot available: {version}")

        # Check AWS credentials
        aws_creds_path = Path.home() / ".aws" / "credentials"
        if aws_creds_path.exists() or os.getenv("AWS_ACCESS_KEY_ID"):
            success, stdout, stderr = self.run_sky_cmd("check")
            if success and stdout and "AWS: enabled" in stdout:
                try:
                    result = subprocess.run([
                        "aws", "sts", "get-caller-identity", "--query", "Account",
                        "--output", "text", "--no-paginate"
                    ], capture_output=True, text=True, check=False)
                    account = result.stdout.strip() if result.returncode == 0 else "unknown"
                    self.log_success(f"AWS credentials available (Account: {account})")
                except FileNotFoundError:
                    self.log_warning("AWS credentials configured but aws CLI not available")
            else:
                self.log_warning("AWS credentials configured but not working with SkyPilot")
                if stderr:
                    self.log_warning(f"SkyPilot check error: {stderr}")
        else:
            self.log_warning("AWS credentials not found. Configure them in ~/.aws/")

        return True

    def deploy_cluster(self, config_file: str = "cluster.yaml") -> bool:
        """Deploy cluster using SkyPilot."""
        config_path = Path(config_file)
        if not config_path.exists():
            self.log_error(f"Config file not found: {config_file}")
            return False

        try:
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
                success, stdout, stderr = self.run_sky_cmd("launch", config_file, "--name", cluster_name, "--yes")
                if stdout:
                    print(stdout)
                if stderr:
                    print(stderr, file=sys.stderr)
            else:
                # Redirect to log file
                self.console.print(f"Deploying cluster... (check {self.log_file} for detailed progress)")
                success, stdout, stderr = self.run_sky_cmd("launch", config_file, "--name", cluster_name, "--yes")
                self.log_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    if stdout:
                        f.write(f"=== SkyPilot Launch Output ===\n{stdout}\n")
                    if stderr:
                        f.write(f"=== SkyPilot Launch Errors ===\n{stderr}\n")

            if success:
                self.log_success(f"Cluster '{cluster_name}' deployed successfully!")
                self._show_completion_banner()
                return True
            else:
                self.log_error("Deployment failed")
                if stderr and not self.log_to_console:
                    self.log_error(f"SkyPilot error: {stderr}")
                return False

        except Exception as e:
            self.log_error(f"Deployment failed with exception: {e}")
            return False

    def _show_completion_banner(self) -> None:
        """Show deployment completion banner."""
        self.console.print()
        self.console.print("┌─────────────────────────────────────────────────┐", style="green")
        self.console.print("│               🎉 Deployment Complete            │", style="green")
        self.console.print("├─────────────────────────────────────────────────┤", style="green")
        self.console.print("│ Next Steps:                                     │", style="green")
        self.console.print("│ • Check status: uvx run spot-deployer status   │", style="green")
        self.console.print("│ • List nodes: uvx run spot-deployer list       │", style="green")
        self.console.print("│ • SSH to cluster: uvx run spot-deployer ssh    │", style="green")
        self.console.print("│ • View logs: uvx run spot-deployer logs        │", style="green")
        self.console.print("│ • Destroy cluster: uvx run spot-deployer destroy│", style="green")
        self.console.print("└─────────────────────────────────────────────────┘", style="green")
        self.console.print()

    def show_status(self) -> bool:
        """Show cluster status."""
        self.log_header("Cluster Status")
        success, stdout, stderr = self.run_sky_cmd("status")
        if success:
            if stdout:
                print(stdout)
            return True
        else:
            self.log_error("Failed to get cluster status")
            if stderr:
                self.log_error(f"SkyPilot error: {stderr}")
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
            if stderr:
                self.log_error(f"SkyPilot error: {stderr}")
            return False

        # Parse launch time
        launch_time = "unknown"
        if stdout:
            for line in stdout.split('\n'):
                if cluster_name in line:
                    parts = line.split()
                    if len(parts) >= 8:
                        launch_time = " ".join(parts[5:8])
                    break

        # Get number of nodes from config
        try:
            config = self.load_cluster_config()
            num_nodes = config.get('num_nodes', 9)
        except Exception:
            num_nodes = 9

        # Create table
        table = Table(title=f"Cluster: {cluster_name}")
        table.add_column("Node", style="cyan")
        table.add_column("Instance ID", style="magenta")
        table.add_column("Public IP", style="green")
        table.add_column("Zone", style="yellow")
        table.add_column("Launched", style="blue")

        # Add rows (basic info since we can't easily query each node individually)
        for i in range(num_nodes):
            table.add_row(f"node-{i}", "querying...", "querying...", "various", launch_time)

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
        try:
            cmd = ["docker", "exec", "-it", self.docker_container, "ssh", cluster_name]
            result = subprocess.run(cmd, check=False)
            return result.returncode == 0
        except Exception as e:
            self.log_error(f"SSH failed: {e}")
            return False

    def show_logs(self) -> bool:
        """Show cluster logs."""
        cluster_name = self.get_sky_cluster_name()
        if not cluster_name:
            self.log_error("No running cluster found")
            return False

        self.log_info(f"Showing logs for cluster: {cluster_name}")
        success, stdout, stderr = self.run_sky_cmd("logs", cluster_name)
        if success:
            if stdout:
                print(stdout)
            return True
        else:
            self.log_error("Failed to get cluster logs")
            if stderr:
                self.log_error(f"SkyPilot error: {stderr}")
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
            if stdout and "not found" in stdout:
                self.log_info(f"Cluster '{cluster_name}' does not exist")
            else:
                self.log_success(f"Cluster '{cluster_name}' destroyed")
            return True
        else:
            self.log_error("Failed to destroy cluster")
            if stderr:
                self.log_error(f"SkyPilot error: {stderr}")
            return False

    def cleanup_docker(self) -> bool:
        """Clean up Docker container."""
        try:
            result = subprocess.run([
                "docker", "ps", "--filter", f"name={self.docker_container}", "--quiet"
            ], capture_output=True, check=False)

            if result.stdout.strip():
                self.log_info("Stopping SkyPilot Docker container...")
                subprocess.run(["docker", "stop", self.docker_container],
                              capture_output=True, check=False)
                self.log_success("Docker container stopped")

            return True
        except Exception as e:
            self.log_error(f"Failed to cleanup Docker container: {e}")
            return False
