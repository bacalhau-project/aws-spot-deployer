"""Destroy command with full Rich UI and concurrent operations."""

import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from threading import Lock
from typing import Any, Dict

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from ..core.config import SimpleConfig
from ..core.state import SimpleStateManager
from ..utils.aws import check_aws_auth
from ..utils.logging import setup_logger
from ..utils.shutdown_handler import ShutdownContext
from ..utils.ui_manager import UIManager


class DestroyManager:
    """Manages instance destruction with live Rich updates."""

    def __init__(self, config: SimpleConfig, state: SimpleStateManager, console: Console):
        self.config = config
        self.state = state
        self.console = console
        self.logger = None
        self.status_lock = Lock()
        self.instance_status: Dict[str, Dict[str, Any]] = {}
        self.start_time = datetime.now()
        self.ui_manager = UIManager(console)

    def initialize_logger(self):
        """Set up logging."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"spot_destroy_{timestamp}.log"
        self.logger = setup_logger("spot_destroyer", log_filename)
        return log_filename

    def has_bacalhau_env(self) -> bool:
        """Check if Bacalhau environment variables are set."""
        # Require both API host and API key for authentication
        return bool(os.environ.get("BACALHAU_API_HOST") and os.environ.get("BACALHAU_API_KEY"))

    def update_status(self, instance_id: str, region: str, status: str, detail: str = ""):
        """Thread-safe status update."""
        with self.status_lock:
            self.instance_status[instance_id] = {
                "region": region,
                "status": status,
                "detail": detail,
                "timestamp": datetime.now(),
            }
            if self.logger:
                self.logger.info(f"[{instance_id}] {status} {detail}")

    def create_status_table(self) -> Table:
        """Create the status table for display."""
        table = self.ui_manager.create_instance_table(
            title="Instance Destruction Status", header_style="bold red"
        )

        # Sort by region for consistent display
        sorted_instances = sorted(
            self.instance_status.items(), key=lambda x: (x[1]["region"], x[0])
        )

        for instance_id, info in sorted_instances:
            # Use UI manager to format status
            status_display = self.ui_manager.format_status(info["status"], info["detail"])

            # Add row with all available data
            self.ui_manager.add_instance_row(
                table,
                info["region"],
                instance_id,
                status_display,
                info.get("type", "unknown"),
                info.get("public_ip", "N/A"),
                info.get("created", "N/A"),
            )

        return table

    def create_summary_panel(self) -> Panel:
        """Create summary panel showing progress."""
        elapsed = (datetime.now() - self.start_time).total_seconds()

        # Count statuses
        total = len(self.instance_status)
        completed = sum(1 for s in self.instance_status.values() if "✓" in s["status"])
        failed = sum(1 for s in self.instance_status.values() if "✗" in s["status"])
        in_progress = total - completed - failed

        content = {
            "title": "Destruction Progress",
            "Total": f"{total} instances",
            "Completed": completed,
            "Failed": failed,
            "In Progress": in_progress,
            "Elapsed": f"{elapsed:.1f}s",
        }

        return self.ui_manager.create_progress_panel("Summary", content)

    def remove_bacalhau_node(self, instance_id: str) -> bool:
        """Remove a Bacalhau node."""
        try:
            api_host = os.environ.get("BACALHAU_API_HOST")
            api_key = os.environ.get("BACALHAU_API_KEY")

            if not api_host or not api_key:
                return False

            # Use bacalhau with the --api-host flag
            cmd = ["bacalhau", "node", "list", "--output", "json", "--api-host", api_host]

            env = os.environ.copy()
            if api_key:
                env["BACALHAU_API_KEY"] = api_key

            result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=10)
            if result.returncode != 0:
                return False

            nodes = json.loads(result.stdout)

            # Find matching node
            node_id_to_remove = None
            for node in nodes:
                node_id = node.get("Info", {}).get("NodeID", "")
                if instance_id in node_id:
                    node_id_to_remove = node_id
                    break

            if not node_id_to_remove:
                return True  # No node found, consider it success

            # Use bacalhau to delete node
            cmd = ["bacalhau", "node", "delete", node_id_to_remove, "--api-host", api_host]
            result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=10)

            return result.returncode == 0

        except Exception:
            return False

    def cleanup_all_disconnected_nodes(self) -> int:
        """Clean up all disconnected Bacalhau nodes."""
        try:
            api_host = os.environ.get("BACALHAU_API_HOST")
            api_key = os.environ.get("BACALHAU_API_KEY")

            if not api_host:
                return 0

            # Use bacalhau with the --api-host flag
            cmd = ["bacalhau", "node", "list", "--output", "json", "--api-host", api_host]

            env = os.environ.copy()
            if api_key:
                env["BACALHAU_API_KEY"] = api_key

            if self.logger:
                self.logger.info(f"Running command: {' '.join(cmd)}")
                self.logger.info(f"Using API host: {api_host}")

            # Add retry logic for Bacalhau API calls
            max_retries = 3
            result = None

            for attempt in range(max_retries):
                try:
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, env=env, timeout=30
                    )
                    if result.returncode == 0:
                        break
                    elif attempt < max_retries - 1:
                        if self.logger:
                            self.logger.info(
                                f"Bacalhau API call failed (attempt {attempt + 1}/{max_retries}), retrying..."
                            )
                        time.sleep(2**attempt)  # Exponential backoff
                except subprocess.TimeoutExpired:
                    if attempt < max_retries - 1:
                        if self.logger:
                            self.logger.info(
                                f"Bacalhau API call timed out (attempt {attempt + 1}/{max_retries}), retrying..."
                            )
                        time.sleep(2**attempt)
                    else:
                        if self.logger:
                            self.logger.error("Bacalhau API call timed out after all retries")
                        return 0

            # Always print debug info
            if self.logger:
                self.logger.debug(f"Command: {' '.join(cmd)}")
                self.logger.debug(f"Exit code: {result.returncode}")

            if result.returncode != 0:
                if self.logger:
                    self.logger.debug(f"stderr: {result.stderr}")
                    self.logger.debug(f"stdout: {result.stdout}")
                if self.logger:
                    self.logger.error(f"Failed to list nodes: {result.stderr}")
                    self.logger.error(f"Command output: {result.stdout}")
                    self.logger.error(f"API Host used: {api_host}")
                return 0

            if self.logger:
                self.logger.debug(f"stdout length: {len(result.stdout)}")
                self.logger.debug(f"stdout: {result.stdout}")

            try:
                nodes = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                if self.logger:
                    self.logger.error(f"Failed to parse node list JSON: {e}")
                    self.logger.error(f"Output was: {result.stdout}")
                print(f"[DEBUG] Failed to parse JSON: {e}")
                print(f"[DEBUG] Output: {result.stdout}")
                return 0

            if self.logger:
                self.logger.debug(f"Successfully parsed {len(nodes)} nodes")

            # Find disconnected compute nodes
            disconnected_nodes = [
                node
                for node in nodes
                if (
                    node.get("Connection") == "DISCONNECTED"
                    and node.get("Info", {}).get("NodeType") == "Compute"
                )
            ]

            if self.logger:
                self.logger.debug(f"Found {len(disconnected_nodes)} disconnected compute nodes")

            if self.logger:
                self.logger.info(
                    f"Found {len(nodes)} total nodes, {len(disconnected_nodes)} disconnected"
                )

            if not disconnected_nodes:
                return 0

            deleted_count = 0
            for node in disconnected_nodes:
                node_id = node.get("Info", {}).get("NodeID", "")
                if node_id:
                    # Use bacalhau to delete node
                    cmd = ["bacalhau", "node", "delete", node_id, "--api-host", api_host]
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, env=env, timeout=10
                    )
                    if result.returncode == 0:
                        deleted_count += 1
                        if self.logger:
                            self.logger.info(f"Deleted disconnected node: {node_id}")
                    else:
                        if self.logger:
                            self.logger.error(f"Failed to delete node {node_id}: {result.stderr}")

            return deleted_count

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error cleaning up disconnected nodes: {e}")
            return 0

    def _check_aws_orphaned_instances(self):
        """Check AWS for any orphaned spot instances that aren't in state file."""
        try:
            from ..utils.aws_manager import AWSResourceManager

            regions_checked = 0
            orphaned_found = 0

            # Get all regions
            regions = [list(r.keys())[0] for r in self.config.regions()]
            self.console.print(f"[dim]Scanning {len(regions)} regions: {', '.join(regions)}[/dim]")

            # Check each region from config
            for region_config in self.config.regions():
                region = list(region_config.keys())[0]
                regions_checked += 1

                self.console.print(f"[dim]  • Checking {region}...[/dim]", end="")

                try:
                    aws_manager = AWSResourceManager(region)

                    # Look for instances with our tags (both old and new tag formats)
                    response = aws_manager.ec2.describe_instances(
                        Filters=[
                            {
                                "Name": "tag:ManagedBy",
                                "Values": ["SpotDeployer", "aws-spot-deployer"],
                            },
                            {
                                "Name": "instance-state-name",
                                "Values": ["running", "pending", "stopping", "stopped"],
                            },
                        ]
                    )

                    found_in_region = 0
                    for reservation in response.get("Reservations", []):
                        for instance in reservation.get("Instances", []):
                            orphaned_found += 1
                            found_in_region += 1
                            instance_id = instance.get("InstanceId", "Unknown")
                            state = instance.get("State", {}).get("Name", "unknown")
                            public_ip = instance.get("PublicIpAddress", "N/A")

                            if found_in_region == 1:
                                self.console.print("")  # New line after region check

                            self.console.print(
                                f"[yellow]    ⚠️  Found orphaned instance: "
                                f"{instance_id} ({state}) - IP: {public_ip}[/yellow]"
                            )

                            # Terminate the orphaned instance
                            if state not in ["terminated", "terminating"]:
                                self.console.print(f"[dim]    → Terminating {instance_id}...[/dim]")
                                try:
                                    aws_manager.ec2.terminate_instances(InstanceIds=[instance_id])
                                    self.console.print(
                                        f"[green]    ✓ Terminated {instance_id}[/green]"
                                    )
                                    if self.logger:
                                        self.logger.info(
                                            f"Terminated orphaned instance {instance_id} in {region}"
                                        )
                                except Exception as e:
                                    self.console.print(
                                        f"[red]    ✗ Failed to terminate {instance_id}[/red]"
                                    )
                                    if self.logger:
                                        self.logger.error(
                                            f"Failed to terminate orphaned instance {instance_id}: {e}"
                                        )

                    if found_in_region == 0:
                        self.console.print(" [green]✓[/green]")

                except Exception as e:
                    self.console.print(" [red]✗[/red]")
                    if self.logger:
                        self.logger.debug(f"Error checking region {region}: {e}")

            self.console.print(f"[dim]Checked {regions_checked} regions[/dim]")

            if orphaned_found > 0:
                self.console.print(
                    f"\n[green]✅ Found and terminated {orphaned_found} orphaned instances[/green]"
                )

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error checking for orphaned instances: {e}")

    def destroy_instance(self, instance: Dict) -> bool:
        """Destroy a single instance and its resources."""
        instance_id = instance["id"]
        region = instance["region"]

        try:
            from ..utils.aws_manager import AWSResourceManager

            aws_manager = AWSResourceManager(region)
            ec2 = aws_manager.ec2

            # First check if instance exists
            instance_state = aws_manager.get_instance_state(instance_id)

            if instance_state in ["terminated", "terminating", "not-found"]:
                self.update_status(instance_id, region, "✓ Terminated", "Already gone")
                return True

            # Step 1: Remove from Bacalhau (if configured)
            if self.has_bacalhau_env():
                self.update_status(instance_id, region, "⏳ Removing from Bacalhau...")
                if self.remove_bacalhau_node(instance_id):
                    self.update_status(instance_id, region, "⏳ Bacalhau removed", "")

            # Step 2: Terminate instance
            self.update_status(instance_id, region, "⏳ Terminating instance...")
            if not aws_manager.terminate_instance(instance_id):
                self.update_status(instance_id, region, "✗ Failed", "Termination failed")
                return False

            # Step 3: Check for VPC
            self.update_status(instance_id, region, "⏳ Checking VPC...")

            # Get instance details to find VPC
            try:
                response = ec2.describe_instances(InstanceIds=[instance_id])
                vpc_id = None
                for reservation in response.get("Reservations", []):
                    for inst in reservation.get("Instances", []):
                        vpc_id = inst.get("VpcId")
                        break

                if vpc_id:
                    # Check if it's a dedicated VPC
                    vpcs = ec2.describe_vpcs(VpcIds=[vpc_id])
                    for vpc in vpcs.get("Vpcs", []):
                        # Extract tags safely
                        tags = {}
                        for tag in vpc.get("Tags", []):
                            if "Key" in tag and "Value" in tag:
                                tags[tag["Key"]] = tag["Value"]
                        if tags.get("ManagedBy") == "SpotDeployer":
                            self.update_status(instance_id, region, "⏳ Deleting VPC...", vpc_id)
                            if aws_manager.delete_vpc_resources(vpc_id):
                                self.update_status(instance_id, region, "✓ Complete", "VPC deleted")
                            else:
                                self.update_status(
                                    instance_id, region, "✓ Complete", "VPC deletion failed"
                                )
                            return True

            except Exception:
                pass

            # No dedicated VPC, just mark as complete
            self.update_status(instance_id, region, "✓ Complete", "")
            return True

        except Exception as e:
            error_msg = str(e)
            if "InsufficientInstanceCapacity" in error_msg:
                error_msg = "No capacity"
            elif len(error_msg) > 30:
                error_msg = error_msg[:30] + "..."

            self.update_status(instance_id, region, "✗ Failed", error_msg)
            return False

    def run(self, verbose: bool = False) -> None:
        """Execute the destruction process."""
        # Check state file
        self.console.print("[dim]Checking local state file for instances...[/dim]")
        instances = self.state.load_instances()

        # Debug environment variables if verbose
        if verbose:
            self.console.print(f"""[dim]Environment variables:[/dim]
[dim]BACALHAU_API_HOST: {os.environ.get("BACALHAU_API_HOST", "NOT SET")}[/dim]
[dim]BACALHAU_API_KEY: {"SET" if os.environ.get("BACALHAU_API_KEY") else "NOT SET"}[/dim]
""")

        # Always check for disconnected Bacalhau nodes first if configured
        if self.has_bacalhau_env():
            self.console.print("[dim]Checking for disconnected Bacalhau nodes...[/dim]")
            deleted = self.cleanup_all_disconnected_nodes()
            if deleted > 0:
                self.console.print(
                    f"[green]✅ Deleted {deleted} disconnected Bacalhau nodes[/green]"
                )
            else:
                self.console.print("[dim]No disconnected nodes found[/dim]")

        # If no instances to destroy, we're done
        if not instances:
            self.console.print("[yellow]ℹ️  No instances found in state file[/yellow]")
            self.console.print("[dim]   State file exists but contains no instance records[/dim]")

            # Also check AWS for any orphaned instances
            self.console.print("\n[dim]Checking AWS for orphaned spot instances...[/dim]")
            self._check_aws_orphaned_instances()
            return

        # Show what we found
        self.console.print(f"[green]Found {len(instances)} instances in state file[/green]")

        # Group by region for summary
        instances_by_region = {}
        for instance in instances:
            region = instance["region"]
            if region not in instances_by_region:
                instances_by_region[region] = []
            instances_by_region[region].append(instance)

        # Show summary by region
        for region, region_instances in instances_by_region.items():
            self.console.print(f"  • {region}: {len(region_instances)} instances")

        # Initialize status for all instances
        for instance in instances:
            self.instance_status[instance["id"]] = {
                "region": instance["region"],
                "status": "⏳ Queued",
                "detail": "",
                "timestamp": datetime.now(),
                "type": instance.get("type", "unknown"),
                "public_ip": instance.get("public_ip", "N/A"),
                "created": instance.get("created", "N/A"),
            }

        # Show warning (but no confirmation needed - user explicitly ran destroy)
        self.console.print(f"\n[bold red]🗑️  Terminating {len(instances)} instances...[/bold red]\n")

        # Check Bacalhau env
        if not self.has_bacalhau_env():
            missing_vars = []
            if not os.environ.get("BACALHAU_API_HOST"):
                missing_vars.append("   - BACALHAU_API_HOST (orchestrator endpoint)")
            if not os.environ.get("BACALHAU_API_KEY"):
                missing_vars.append("   - BACALHAU_API_KEY (authentication)")

            self.console.print(f"""[yellow]⚠️  WARNING: Bacalhau node cleanup disabled[/yellow]
[dim]   Missing environment variables:
{chr(10).join(f"[dim]{var}[/dim]" for var in missing_vars)}
   Disconnected nodes will remain in the Bacalhau cluster.[/dim]
""")

        # Create layout
        def generate_layout() -> Layout:
            layout = Layout()
            layout.split_column(
                Layout(self.create_status_table(), ratio=4),
                Layout(self.create_summary_panel(), size=8),
            )
            return layout

        # Initialize logger
        log_filename = self.initialize_logger()

        # Process instances with max concurrency of 10
        with ShutdownContext("Saving instance destruction state...") as shutdown_ctx:
            # Define cleanup function
            def cleanup_on_shutdown():
                if self.logger:
                    self.logger.warning("Shutdown requested - saving current state...")
                # Save state with any instances that were successfully destroyed
                self.state.save_instances(self.state.load_instances())
                # Update status for any pending instances
                with self.lock:
                    for instance_id, status in self.instance_status.items():
                        if "⏳" in status["status"]:
                            status["status"] = "⚠️ INTERRUPTED"
                            status["detail"] = "Shutdown requested"

            shutdown_ctx.add_cleanup(cleanup_on_shutdown)

            with Live(
                generate_layout(),
                refresh_per_second=4,
                console=self.console,
                screen=True,
                redirect_stdout=False,
            ) as live:
                with ThreadPoolExecutor(max_workers=min(10, len(instances))) as executor:
                    # Submit all tasks
                    future_to_instance = {
                        executor.submit(self.destroy_instance, instance): instance
                        for instance in instances
                        if not shutdown_ctx.shutdown_requested  # Don't submit new tasks if shutting down
                    }

                    # Process as they complete
                    for future in as_completed(future_to_instance):
                        if shutdown_ctx.shutdown_requested:
                            # Cancel remaining futures
                            for f in future_to_instance:
                                if not f.done():
                                    f.cancel()
                            break

                        instance = future_to_instance[future]
                        try:
                            success = future.result()
                            # Always remove from state if terminated or not found
                            if success or "Terminated" in self.instance_status.get(
                                instance["id"], {}
                            ).get("status", ""):
                                self.state.remove_instance(instance["id"])
                        except Exception as e:
                            # Still try to remove from state if instance doesn't exist
                            if "InvalidInstanceID" in str(e):
                                self.state.remove_instance(instance["id"])

                        # Update display
                        live.update(generate_layout())

                # Final update
                live.update(generate_layout())

        # Show summary
        total = len(instances)
        completed = sum(1 for s in self.instance_status.values() if "✓" in s["status"])
        failed = total - completed

        summary_lines = ["\n[bold]Destruction Summary:[/bold]"]
        if completed == total:
            summary_lines.append(f"[green]✅ All {total} instances destroyed successfully[/green]")
        else:
            summary_lines.append(f"[yellow]⚠️  {completed}/{total} instances destroyed[/yellow]")
            if failed > 0:
                summary_lines.append(f"[red]❌ {failed} instances failed[/red]")
        self.console.print("\n".join(summary_lines))

        # Clean up all disconnected nodes if Bacalhau is configured
        # Do second Bacalhau cleanup only if we destroyed instances
        if self.has_bacalhau_env() and completed > 0:
            # Wait for nodes to disconnect
            self.console.print(
                """\n[dim]Waiting 10 seconds for Bacalhau nodes to disconnect...[/dim]"""
            )
            import time

            time.sleep(10)

            self.console.print("[dim]Cleaning up disconnected Bacalhau nodes...[/dim]")
            deleted = self.cleanup_all_disconnected_nodes()
            if deleted > 0:
                self.console.print(
                    f"[green]✅ Deleted {deleted} disconnected Bacalhau nodes[/green]"
                )
            else:
                self.console.print("[dim]No disconnected nodes found[/dim]")

        self.console.print(f"\n[dim]Destruction log saved to: {log_filename}[/dim]")


def cmd_destroy(config: SimpleConfig, state: SimpleStateManager, verbose: bool = False) -> None:
    """Destroy all instances with enhanced UI."""
    if not check_aws_auth():
        return

    # Create console and let Rich handle terminal detection
    console = Console(
        force_terminal=True,
        force_interactive=True,
        legacy_windows=False,
    )
    manager = DestroyManager(config, state, console)
    manager.run(verbose=verbose)
