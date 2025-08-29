"""
SkyPilot Cluster Manager - Core cluster operations.

Handles Docker container management, SkyPilot interactions, and cluster lifecycle.
Uses proper YAML parsing and Rich output instead of fragile bash scripting.
"""

import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
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

    def log(self, level: str, message: str, style: str = "") -> None:
        """Log message to console and/or file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if self.log_to_console:
            self.console.print(f"[{level}] {message}", style=style)
        else:
            # Write to file
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, "a", encoding="utf-8") as f:
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
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, "a", encoding="utf-8") as f:
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
            with open(config_path, encoding="utf-8") as f:
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
            return str(config.get("name", "cluster"))
        except Exception:
            return "cluster"

    def ensure_docker_container(self) -> bool:
        """Ensure Docker container is running."""
        try:
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
                check=False,
            )

            if result.stdout.strip():
                return True  # Container already running

            self.log_info("Starting SkyPilot Docker container...")

            # Remove any existing stopped container
            subprocess.run(
                ["docker", "rm", self.docker_container],
                capture_output=True,
                stderr=subprocess.DEVNULL,
                check=False,
            )

            # Start new container
            home = Path.home()
            cwd = Path.cwd()

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
                clusters = data.get("clusters", [])
                if clusters and isinstance(clusters, list):
                    cluster_name = clusters[0].get("name")
                    return str(cluster_name) if cluster_name else None
            except json.JSONDecodeError:
                pass

        # Fallback to text parsing
        success, stdout, stderr = self.run_sky_cmd("status")
        if success and stdout:
            for line in stdout.split("\n"):
                line = line.strip()
                if line and not line.startswith(("NAME", "Enabled", "No", "Clusters")):
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
        except subprocess.CalledProcessError as e:
            self.log_error(f"Docker check failed: {e}")
            return False
        except FileNotFoundError:
            self.log_error("Docker not found. Please install Docker.")
            return False

        # Check SkyPilot image
        self.log_info("Ensuring SkyPilot Docker image is available...")
        try:
            result = subprocess.run(
                ["docker", "image", "inspect", self.skypilot_image],
                capture_output=True,
                check=False,
            )

            if result.returncode != 0:
                self.log_info("Pulling SkyPilot Docker image...")
                result = subprocess.run(
                    ["docker", "pull", self.skypilot_image], check=False
                )
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

        version = stdout.split("\n")[0] if stdout else "unknown"
        self.log_success(f"SkyPilot available: {version}")

        # Check AWS credentials - this should fail fast to prevent deployment errors
        aws_creds_path = Path.home() / ".aws" / "credentials"
        if aws_creds_path.exists() or os.getenv("AWS_ACCESS_KEY_ID"):
            success, stdout, stderr = self.run_sky_cmd("check")
            if success and stdout and "AWS: enabled" in stdout:
                try:
                    aws_result = subprocess.run(
                        [
                            "aws",
                            "sts",
                            "get-caller-identity",
                            "--query",
                            "Account",
                            "--output",
                            "text",
                            "--no-paginate",
                        ],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    account = (
                        aws_result.stdout.strip()
                        if aws_result.returncode == 0
                        else "unknown"
                    )
                    self.log_success(f"AWS credentials available (Account: {account})")
                except FileNotFoundError:
                    self.log_error(
                        "AWS credentials configured but aws CLI not available"
                    )
                    return False
            else:
                self.log_error(
                    "AWS credentials configured but not working with SkyPilot"
                )
                if stderr:
                    self.log_error(f"SkyPilot check error: {stderr}")
                self.log_error("Fix AWS credentials before deployment. Common fixes:")
                self.log_error("  - Run: aws sso login")
                self.log_error("  - Or check: aws sts get-caller-identity")
                self.log_error("  - Or verify ~/.aws/credentials")
                return False
        else:
            self.log_error("AWS credentials not found. Configure them in ~/.aws/")
            self.log_error(
                "Run 'aws configure' or 'aws sso login' to set up credentials"
            )
            return False

        return True

    def _parse_deployment_log_line(self, line: str) -> Optional[dict[str, Any]]:
        """Parse a single log line to extract node information."""
        # Pattern: (worker8, rank=8, pid=2816, ip=172.31.41.250) message
        pattern = r"\(([^,]+),\s*rank=(\d+),\s*pid=\d+,\s*ip=([^)]+)\)\s*(.*)"
        match = re.match(pattern, line)

        if match:
            node_name, rank, ip, message = match.groups()
            return {
                "node": node_name,
                "rank": int(rank),
                "ip": ip,
                "message": message.strip(),
                "timestamp": time.time(),
            }
        return None

    def _create_deployment_table(self, nodes: dict[str, dict[str, Any]]) -> Table:
        """Create a Rich table showing deployment progress."""
        table = Table(title="🌍 Global Cluster Deployment Progress", show_header=True)
        table.add_column("Node", style="bold blue", width=12)
        table.add_column("Rank", justify="center", width=6)
        table.add_column("IP Address", style="cyan", width=15)
        table.add_column("Status", width=40)
        table.add_column("Last Update", style="dim", width=12)

        # Sort nodes by rank
        sorted_nodes = sorted(nodes.items(), key=lambda x: x[1].get("rank", 999))

        for node_id, info in sorted_nodes:
            # Determine status from recent messages
            status = self._get_node_status(info)
            status_color = self._get_status_color(status)

            # Format last update time
            last_update = info.get("timestamp", 0)
            time_ago = (
                f"{int(time.time() - last_update)}s ago"
                if last_update > 0
                else "Unknown"
            )

            table.add_row(
                info.get("node", node_id),
                str(info.get("rank", "?")),
                info.get("ip", "Unknown"),
                f"[{status_color}]{status}[/{status_color}]",
                time_ago,
            )

        return table

    def _get_node_status(self, node_info: dict[str, Any]) -> str:
        """Determine node status from recent messages."""
        recent_messages = node_info.get("recent_messages", [])
        if not recent_messages:
            return "Initializing"

        latest_message = recent_messages[-1].lower()

        # Check for specific status indicators
        if "deployment complete" in latest_message:
            return "✅ Deployed"
        elif "health check summary" in latest_message:
            return "🔍 Health Check"
        elif "bacalhau node running" in latest_message:
            return "🚀 Bacalhau Started"
        elif "docker daemon is running" in latest_message:
            return "🐳 Docker Ready"
        elif "pulling" in latest_message or "pull" in latest_message:
            return "📦 Pulling Images"
        elif "starting" in latest_message or "start" in latest_message:
            return "⚡ Starting Services"
        elif "error" in latest_message or "failed" in latest_message:
            return "❌ Error"
        elif "warning" in latest_message:
            return "⚠️ Warning"
        else:
            return "🔄 Working"

    def _get_status_color(self, status: str) -> str:
        """Get Rich color for status."""
        if "✅" in status:
            return "green"
        elif "❌" in status:
            return "red"
        elif "⚠️" in status:
            return "yellow"
        elif "🔄" in status or "⚡" in status or "🚀" in status:
            return "blue"
        elif "🐳" in status or "📦" in status:
            return "cyan"
        else:
            return "white"

    def _monitor_deployment_progress(self, log_file_path: Path) -> None:
        """Monitor deployment log file and update progress display."""
        nodes: dict[str, dict[str, Any]] = {}

        try:
            with Live(
                self._create_deployment_table(nodes), refresh_per_second=2
            ) as live:
                last_position = 0

                # Monitor for up to 20 minutes
                start_time = time.time()
                timeout = 20 * 60  # 20 minutes

                while time.time() - start_time < timeout:
                    try:
                        if log_file_path.exists():
                            with open(log_file_path) as f:
                                f.seek(last_position)
                                new_lines = f.readlines()
                                last_position = f.tell()

                                for line in new_lines:
                                    node_info = self._parse_deployment_log_line(
                                        line.strip()
                                    )
                                    if node_info:
                                        node_id = (
                                            f"{node_info['node']}-{node_info['rank']}"
                                        )

                                        if node_id not in nodes:
                                            nodes[node_id] = {
                                                "node": node_info["node"],
                                                "rank": node_info["rank"],
                                                "ip": node_info["ip"],
                                                "recent_messages": [],
                                                "timestamp": node_info["timestamp"],
                                            }

                                        # Update node info
                                        nodes[node_id]["ip"] = node_info["ip"]
                                        nodes[node_id]["timestamp"] = node_info[
                                            "timestamp"
                                        ]

                                        # Keep last 5 messages for status determination
                                        nodes[node_id]["recent_messages"].append(
                                            node_info["message"]
                                        )
                                        if len(nodes[node_id]["recent_messages"]) > 5:
                                            nodes[node_id]["recent_messages"].pop(0)

                                        # Update the display
                                        live.update(
                                            self._create_deployment_table(nodes)
                                        )

                        time.sleep(1)  # Check for updates every second

                    except Exception:
                        # Continue monitoring even if there are parsing errors
                        continue

        except KeyboardInterrupt:
            # User interrupted - that's fine
            pass

    def _monitor_deployment_progress_streaming(self, cluster_name: str) -> None:
        """Monitor deployment progress using SkyPilot's streaming logs."""
        nodes: dict[str, dict[str, Any]] = {}

        try:
            # Show initial status
            initial_panel = Panel(
                "🔄 Starting deployment monitoring...\nWaiting for cluster activity...",
                title="🌍 Deployment Monitor",
                border_style="blue",
            )

            with Live(initial_panel, refresh_per_second=2) as live:
                start_time = time.time()
                timeout = 20 * 60  # 20 minutes
                last_activity = start_time

                while time.time() - start_time < timeout:
                    try:
                        # Check if cluster exists first
                        check_success, check_stdout, _ = self.run_sky_cmd(
                            "status", cluster_name
                        )

                        if check_success and check_stdout:
                            # Cluster exists, try to get logs
                            log_success, log_stdout, log_stderr = self.run_sky_cmd(
                                "logs", cluster_name, "--tail=20"
                            )

                            if log_success and log_stdout:
                                last_activity = time.time()

                                # Parse log lines for node info
                                new_nodes_found = False
                                for line in log_stdout.split("\n"):
                                    line = line.strip()
                                    if not line:
                                        continue

                                    node_info = self._parse_deployment_log_line(line)
                                    if node_info:
                                        node_id = (
                                            f"{node_info['node']}-{node_info['rank']}"
                                        )

                                        if node_id not in nodes:
                                            nodes[node_id] = {
                                                "node": node_info["node"],
                                                "rank": node_info["rank"],
                                                "ip": node_info["ip"],
                                                "recent_messages": [],
                                                "timestamp": node_info["timestamp"],
                                            }
                                            new_nodes_found = True

                                        # Update node info
                                        nodes[node_id]["ip"] = node_info["ip"]
                                        nodes[node_id]["timestamp"] = node_info[
                                            "timestamp"
                                        ]

                                        # Keep last 5 messages for status determination
                                        nodes[node_id]["recent_messages"].append(
                                            node_info["message"]
                                        )
                                        if len(nodes[node_id]["recent_messages"]) > 5:
                                            nodes[node_id]["recent_messages"].pop(0)

                                # Update display if we have nodes
                                if nodes:
                                    live.update(self._create_deployment_table(nodes))
                                elif new_nodes_found:
                                    live.update(self._create_deployment_table(nodes))

                            # If we haven't seen activity in 5 minutes, show waiting message
                            elif time.time() - last_activity > 300:
                                waiting_panel = Panel(
                                    f"⏳ Waiting for deployment activity...\n"
                                    f"Cluster: {cluster_name}\n"
                                    f"Elapsed: {int(time.time() - start_time)}s\n"
                                    f"Last activity: {int(time.time() - last_activity)}s ago",
                                    title="🌍 Deployment Monitor",
                                    border_style="yellow",
                                )
                                if (
                                    not nodes
                                ):  # Only show if we don't have nodes to display
                                    live.update(waiting_panel)

                        else:
                            # Cluster doesn't exist yet
                            waiting_panel = Panel(
                                f"🔄 Waiting for cluster creation...\n"
                                f"Cluster: {cluster_name}\n"
                                f"Elapsed: {int(time.time() - start_time)}s",
                                title="🌍 Deployment Monitor",
                                border_style="blue",
                            )
                            if not nodes:  # Only show if we don't have nodes to display
                                live.update(waiting_panel)

                    except Exception as e:
                        # Log errors but continue monitoring
                        if time.time() - start_time > 30:  # Only show errors after 30s
                            error_panel = Panel(
                                f"⚠️  Monitor error (continuing): {str(e)}\n"
                                f"Elapsed: {int(time.time() - start_time)}s",
                                title="🌍 Deployment Monitor",
                                border_style="red",
                            )
                            if not nodes:  # Only show if we don't have nodes to display
                                live.update(error_panel)

                    # Sleep before next check
                    time.sleep(3)

        except KeyboardInterrupt:
            # User interrupted - that's fine
            pass

    def _extract_node_info_from_logs(self) -> dict[str, dict[str, Any]]:
        """Extract node information from recent cluster logs."""
        cluster_name = self.get_sky_cluster_name()
        if not cluster_name:
            return {}

        try:
            # Get recent logs
            success, stdout, stderr = self.run_sky_cmd(
                "logs", cluster_name, "--tail=100"
            )
            if not success or not stdout:
                return {}

            nodes: dict[str, dict[str, Any]] = {}

            for line in stdout.split("\n"):
                node_info = self._parse_deployment_log_line(line.strip())
                if node_info:
                    node_id = f"{node_info['node']}-{node_info['rank']}"
                    nodes[node_id] = node_info

            return nodes
        except Exception:
            return {}

    def deploy_cluster(
        self, config_file: str = "cluster.yaml", follow: bool = False
    ) -> bool:
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
                # Show output when --console flag used
                success, stdout, stderr = self.run_sky_cmd(
                    "launch", config_file, "--name", cluster_name, "--yes"
                )
                if stdout:
                    print(stdout)
                if stderr:
                    print(stderr, file=sys.stderr)
            elif follow:
                # Follow mode - real-time monitoring UI
                self.console.print(
                    "🚀 Starting deployment with real-time progress monitor..."
                )
                self.console.print(f"📄 Detailed logs: {self.log_file}")
                self.console.print(
                    "💡 [dim]Tip: Use 'amauo create' (without --follow) to run in background[/dim]"
                )

                # Ensure log file directory exists
                self.log_file.parent.mkdir(parents=True, exist_ok=True)

                # Start streaming progress monitor in background thread
                monitor_thread = None
                try:
                    monitor_thread = threading.Thread(
                        target=self._monitor_deployment_progress_streaming,
                        args=(cluster_name,),
                        daemon=True,
                    )
                    monitor_thread.start()

                    # Give monitor a moment to start
                    time.sleep(2)

                    # Run deployment (the streaming monitor will track progress)
                    success, stdout, stderr = self.run_sky_cmd(
                        "launch", config_file, "--name", cluster_name, "--yes"
                    )

                    # Log output to file
                    with open(self.log_file, "a", encoding="utf-8") as f:
                        if stdout:
                            f.write(f"=== SkyPilot Launch Output ===\n{stdout}\n")
                        if stderr:
                            f.write(f"=== SkyPilot Launch Errors ===\n{stderr}\n")

                except Exception as e:
                    self.log_error(f"Deployment monitoring error: {e}")
                    success, stdout, stderr = self.run_sky_cmd(
                        "launch", config_file, "--name", cluster_name, "--yes"
                    )
                finally:
                    # Wait a bit for final status updates
                    if monitor_thread and monitor_thread.is_alive():
                        time.sleep(3)
            else:
                # Default background mode - start deployment and return immediately
                self.console.print(
                    "🚀 [green]Starting deployment in background...[/green]"
                )
                self.console.print(f"📄 Logs: {self.log_file}")
                self.console.print(
                    "💡 [dim]Use 'amauo monitor --follow' to track progress[/dim]"
                )

                # Ensure log file directory exists
                self.log_file.parent.mkdir(parents=True, exist_ok=True)

                # Start SkyPilot deployment in background using detached docker exec
                cmd = [
                    "docker",
                    "exec",
                    "-d",
                    self.docker_container,
                    "sky",
                    "launch",
                    config_file,
                    "--name",
                    cluster_name,
                    "--yes",
                ]

                try:
                    # Start the process in detached mode (-d flag to docker exec)
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, check=False
                    )

                    if result.returncode == 0:
                        success = True
                        self.console.print(
                            "✅ [green]Deployment started successfully![/green]"
                        )
                        # Write initial log entry
                        with open(self.log_file, "a", encoding="utf-8") as f:
                            f.write("=== Deployment Started ===\n")
                            f.write(f"Cluster: {cluster_name}\n")
                            f.write(f"Config: {config_file}\n")
                            f.write(f"Started at: {datetime.now().isoformat()}\n")
                            f.write(
                                "Use 'amauo monitor --follow' to track progress\n\n"
                            )
                    else:
                        success = False
                        self.console.print("❌ [red]Failed to start deployment[/red]")
                        if result.stderr:
                            self.console.print(f"[red]Error: {result.stderr}[/red]")

                except Exception as e:
                    success = False
                    self.console.print(f"❌ [red]Failed to start deployment: {e}[/red]")

            if success:
                if not follow:
                    # Background mode - deployment started, not completed
                    self.log_success(f"Deployment started for cluster '{cluster_name}'")
                    self.console.print(
                        "\n💡 [dim]Deployment is running in background[/dim]"
                    )
                    self.console.print(
                        "🔍 [dim]Use 'amauo monitor' to check status[/dim]"
                    )
                    self.console.print(
                        "📋 [dim]Use 'amauo monitor --follow' for live updates[/dim]"
                    )
                else:
                    # Follow mode - deployment completed
                    self.log_success(f"Cluster '{cluster_name}' deployed successfully!")
                    self._show_completion_banner()
                return True
            else:
                self.log_error(
                    "Deployment failed to start" if not follow else "Deployment failed"
                )
                return False

        except Exception as e:
            self.log_error(f"Deployment failed with exception: {e}")
            return False

    def _show_completion_banner(self) -> None:
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
            "│ • Check status: uvx spot-deployer status   │", style="green"
        )
        self.console.print(
            "│ • List nodes: uvx spot-deployer list       │", style="green"
        )
        self.console.print(
            "│ • SSH to cluster: uvx spot-deployer ssh    │", style="green"
        )
        self.console.print(
            "│ • View logs: uvx spot-deployer logs        │", style="green"
        )
        self.console.print(
            "│ • Destroy cluster: uvx spot-deployer destroy│", style="green"
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
        success, stdout, stderr = self.run_sky_cmd("status", cluster_name)
        if not success:
            self.log_error("Failed to get cluster information")
            if stderr:
                self.log_error(f"SkyPilot error: {stderr}")
            return False

        # Parse launch time
        launch_time = "unknown"
        if stdout:
            for line in stdout.split("\n"):
                if cluster_name in line:
                    parts = line.split()
                    if len(parts) >= 8:
                        launch_time = " ".join(parts[5:8])
                    break

        # Get number of nodes from config
        try:
            config = self.load_cluster_config()
            num_nodes = config.get("num_nodes", 9)
        except Exception:
            num_nodes = 9

        # Create table
        table = Table(title=f"Cluster: {cluster_name}")
        table.add_column("Node", style="cyan")
        table.add_column("Instance ID", style="magenta")
        table.add_column("Public IP", style="green")
        table.add_column("Zone", style="yellow")
        table.add_column("Launched", style="blue")

        # Try to get real node information from recent logs
        nodes_info = self._extract_node_info_from_logs()

        if nodes_info:
            # Show real node data from logs
            for node_id, info in nodes_info.items():
                table.add_row(
                    info.get("node", node_id),
                    f"rank-{info.get('rank', '?')}",
                    f"{info.get('ip', 'unknown')} (private)",
                    "AWS VPC",
                    launch_time,
                )
        else:
            # Fallback to generic info
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

    def monitor_deployments(self, follow: bool = False) -> bool:
        """Monitor active deployments and cluster health."""
        try:
            self.console.print(
                "\n🔍 [bold cyan]Deployment Health Monitor[/bold cyan]\n"
            )

            # Check if SkyPilot container is running
            if not self.ensure_docker_container():
                self.log_error("SkyPilot container not available")
                return False

            # Get cluster status
            success, stdout, stderr = self.run_sky_cmd("status")
            if not success:
                self.log_error(f"Failed to get cluster status: {stderr}")
                return False

            # Parse and display cluster information
            lines = stdout.split("\n")
            clusters_found = []

            # Find cluster information
            in_clusters_section = False
            for line in lines:
                if "NAME" in line and "INFRA" in line and "RESOURCES" in line:
                    in_clusters_section = True
                    continue
                elif in_clusters_section and line.strip():
                    # Stop if we hit another section
                    if line.startswith("Managed jobs") or line.startswith("Services"):
                        break
                    # Look for cluster lines (they contain status info)
                    if any(
                        status in line for status in ["INIT", "UP", "STOPPED", "DOWN"]
                    ):
                        clusters_found.append(line.strip())

            if not clusters_found:
                self.console.print("✅ [green]No active clusters found[/green]")
                return True

            # Display cluster status
            self.console.print("📊 [bold]Active Clusters:[/bold]")
            for cluster_line in clusters_found:
                parts = cluster_line.split()
                if len(parts) >= 3:
                    name = parts[0]

                    # Find status in the line
                    if "INIT" in cluster_line:
                        status_color = "yellow"
                        status_icon = "🔄"
                        health = "Initializing"
                    elif "UP" in cluster_line:
                        status_color = "green"
                        status_icon = "✅"
                        health = "Running"
                    elif "STOPPED" in cluster_line:
                        status_color = "red"
                        status_icon = "⏹️"
                        health = "Stopped"
                    else:
                        status_color = "gray"
                        status_icon = "❓"
                        health = "Unknown"

                    # Extract infrastructure and resources
                    infra = parts[1] if len(parts) > 1 else "Unknown"
                    resources_start = (
                        cluster_line.find(parts[2]) if len(parts) > 2 else -1
                    )
                    status_start = (
                        cluster_line.rfind("INIT")
                        if "INIT" in cluster_line
                        else cluster_line.rfind("UP")
                        if "UP" in cluster_line
                        else -1
                    )

                    if resources_start != -1 and status_start != -1:
                        resources = cluster_line[resources_start:status_start].strip()
                    elif len(parts) > 2:
                        resources = parts[2]
                    else:
                        resources = "Unknown"

                    self.console.print(
                        f"  {status_icon} [{status_color}]{name}[/{status_color}] - {health}"
                    )
                    self.console.print(f"     Infrastructure: {infra}")
                    self.console.print(f"     Resources: {resources}")

            # Check for managed jobs
            job_success, job_stdout, job_stderr = self.run_sky_cmd("jobs", "queue")
            if job_success and "No in-progress managed jobs" not in job_stdout:
                self.console.print("\n⚡ [bold]Active Managed Jobs:[/bold]")
                job_lines = job_stdout.split("\n")
                for line in job_lines:
                    if line.strip() and "job" in line.lower():
                        self.console.print(f"  🔄 {line.strip()}")

            # If following, monitor continuously
            if follow:
                self.console.print(
                    "\n👀 [dim]Monitoring continuously (Ctrl+C to exit)...[/dim]"
                )

                # Use the existing streaming monitor but for active clusters
                active_cluster = None
                for cluster_line in clusters_found:
                    if "INIT" in cluster_line:
                        parts = cluster_line.split()
                        active_cluster = parts[0]
                        break

                if active_cluster:
                    self.console.print(
                        f"🔍 [blue]Following deployment of: {active_cluster}[/blue]"
                    )
                    self._monitor_deployment_progress_streaming(active_cluster)
                else:
                    # Just refresh status periodically
                    import time

                    while True:
                        time.sleep(5)
                        # Re-run status check
                        success, stdout, stderr = self.run_sky_cmd("status")
                        if success:
                            timestamp = time.strftime("%H:%M:%S")
                            self.console.print(
                                f"[dim]{timestamp} - Cluster status updated[/dim]"
                            )

            return True

        except KeyboardInterrupt:
            self.console.print("\n[yellow]⚠️  Monitoring stopped by user[/yellow]")
            return True
        except Exception as e:
            self.log_error(f"Monitoring failed: {e}")
            return False

    def cleanup_docker(self) -> bool:
        """Clean up Docker container."""
        try:
            result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "--filter",
                    f"name={self.docker_container}",
                    "--quiet",
                ],
                capture_output=True,
                check=False,
            )

            if result.stdout.strip():
                self.log_info("Stopping SkyPilot Docker container...")
                subprocess.run(
                    ["docker", "stop", self.docker_container],
                    capture_output=True,
                    check=False,
                )
                self.log_success("Docker container stopped")

            return True
        except Exception as e:
            self.log_error(f"Failed to cleanup Docker container: {e}")
            return False
