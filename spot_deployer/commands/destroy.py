"""Destroy command with full Rich UI and concurrent operations."""
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import subprocess
import json
from typing import Dict
from threading import Lock

import boto3
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.console import Console

from ..core.config import SimpleConfig
from ..core.state import SimpleStateManager
from ..utils.aws import check_aws_auth, delete_deployment_vpc
from ..utils.logging import setup_logger


class DestroyManager:
    """Manages instance destruction with live Rich updates."""
    
    def __init__(self, config: SimpleConfig, state: SimpleStateManager, console: Console):
        self.config = config
        self.state = state
        self.console = console
        self.logger = None
        self.status_lock = Lock()
        self.instance_status = {}
        self.start_time = datetime.now()
        
    def initialize_logger(self):
        """Set up logging."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"spot_destroy_{timestamp}.log"
        self.logger = setup_logger("spot_destroyer", log_filename)
        return log_filename
        
    def has_bacalhau_env(self) -> bool:
        """Check if Bacalhau environment variables are set."""
        return bool(os.environ.get("BACALHAU_API_HOST") and os.environ.get("BACALHAU_API_KEY"))
        
    def update_status(self, instance_id: str, region: str, status: str, detail: str = ""):
        """Thread-safe status update."""
        with self.status_lock:
            self.instance_status[instance_id] = {
                "region": region,
                "status": status,
                "detail": detail,
                "timestamp": datetime.now()
            }
            if self.logger:
                self.logger.info(f"[{instance_id}] {status} {detail}")
                
    def create_status_table(self) -> Table:
        """Create the status table for display."""
        table = Table(show_header=True, header_style="bold red", title="Instance Destruction Status")
        table.add_column("Region", style="magenta", width=15)
        table.add_column("Instance ID", style="cyan", width=20)
        table.add_column("Status", width=25)
        table.add_column("Details", style="dim", width=40)
        
        # Sort by region for consistent display
        sorted_instances = sorted(self.instance_status.items(), key=lambda x: (x[1]["region"], x[0]))
        
        for instance_id, info in sorted_instances:
            status = info["status"]
            
            # Color code the status
            if "✓" in status or "SUCCESS" in status.upper():
                status_display = f"[green]{status}[/green]"
            elif "✗" in status or "ERROR" in status.upper() or "FAILED" in status.upper():
                status_display = f"[red]{status}[/red]"
            elif "⏳" in status or "..." in status:
                status_display = f"[yellow]{status}[/yellow]"
            else:
                status_display = f"[dim]{status}[/dim]"
                
            table.add_row(
                info["region"],
                instance_id,
                status_display,
                info["detail"][:40] + "..." if len(info["detail"]) > 40 else info["detail"]
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
        
        summary = f"""[bold]Destruction Progress[/bold]
        
Total: {total} instances
[green]Completed: {completed}[/green]
[red]Failed: {failed}[/red]
[yellow]In Progress: {in_progress}[/yellow]

Elapsed: {elapsed:.1f}s"""
        
        return Panel(summary, title="Summary", border_style="blue")
        
    def remove_bacalhau_node(self, instance_id: str) -> bool:
        """Remove a Bacalhau node."""
        try:
            api_host = os.environ.get("BACALHAU_API_HOST")
            api_key = os.environ.get("BACALHAU_API_KEY")
            
            if not api_host or not api_key:
                return False
                
            # Get node list
            cmd = ["bacalhau", "node", "list", "--output", "json", "-c", f"API.Host={api_host}"]
            env = os.environ.copy()
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
                
            # Delete the node
            cmd = ["bacalhau", "node", "delete", node_id_to_remove, "-c", f"API.Host={api_host}"]
            result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=10)
            
            return result.returncode == 0
            
        except Exception:
            return False
            
    def destroy_instance(self, instance: Dict) -> bool:
        """Destroy a single instance and its resources."""
        instance_id = instance["id"]
        region = instance["region"]
        
        try:
            ec2 = boto3.client("ec2", region_name=region)
            
            # Step 1: Remove from Bacalhau (if configured)
            if self.has_bacalhau_env():
                self.update_status(instance_id, region, "⏳ Removing from Bacalhau...")
                if self.remove_bacalhau_node(instance_id):
                    self.update_status(instance_id, region, "⏳ Bacalhau removed", "")
            
            # Step 2: Terminate instance
            self.update_status(instance_id, region, "⏳ Terminating instance...")
            ec2.terminate_instances(InstanceIds=[instance_id])
            
            # Step 3: Check for VPC
            self.update_status(instance_id, region, "⏳ Checking VPC...")
            
            # Get instance details to find VPC
            try:
                response = ec2.describe_instances(InstanceIds=[instance_id])
                vpc_id = None
                for reservation in response["Reservations"]:
                    for inst in reservation["Instances"]:
                        vpc_id = inst.get("VpcId")
                        break
                        
                if vpc_id:
                    # Check if it's a dedicated VPC
                    vpcs = ec2.describe_vpcs(VpcIds=[vpc_id])
                    for vpc in vpcs["Vpcs"]:
                        tags = {tag["Key"]: tag["Value"] for tag in vpc.get("Tags", [])}
                        if tags.get("ManagedBy") == "SpotDeployer":
                            self.update_status(instance_id, region, "⏳ Deleting VPC...", vpc_id)
                            if delete_deployment_vpc(ec2, vpc_id):
                                self.update_status(instance_id, region, "✓ Complete", "VPC deleted")
                            else:
                                self.update_status(instance_id, region, "✓ Complete", "VPC deletion failed")
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
            
    def run(self) -> None:
        """Execute the destruction process."""
        instances = self.state.load_instances()
        if not instances:
            self.console.print("[yellow]No instances to destroy.[/yellow]")
            return
            
        # Initialize status for all instances
        for instance in instances:
            self.instance_status[instance["id"]] = {
                "region": instance["region"],
                "status": "⏳ Queued",
                "detail": "",
                "timestamp": datetime.now()
            }
            
        # Show warning
        self.console.print(f"\n[bold red]⚠️  WARNING: This will terminate {len(instances)} instances[/bold red]\n")
        
        # Check Bacalhau env
        if not self.has_bacalhau_env():
            self.console.print("[dim]Note: Bacalhau node cleanup disabled (no API credentials set)[/dim]\n")
        
        # Create layout
        def generate_layout() -> Layout:
            layout = Layout()
            layout.split_column(
                Layout(self.create_status_table(), ratio=3),
                Layout(self.create_summary_panel(), ratio=1)
            )
            return layout
            
        # Initialize logger
        log_filename = self.initialize_logger()
        
        # Process instances with max concurrency of 10
        with Live(generate_layout(), refresh_per_second=4, console=self.console) as live:
            with ThreadPoolExecutor(max_workers=min(10, len(instances))) as executor:
                # Submit all tasks
                future_to_instance = {
                    executor.submit(self.destroy_instance, instance): instance
                    for instance in instances
                }
                
                # Process as they complete
                for future in as_completed(future_to_instance):
                    instance = future_to_instance[future]
                    success = future.result()
                    
                    if success:
                        # Remove from state
                        self.state.remove_instance(instance["id"])
                    
                    # Update display
                    live.update(generate_layout())
            
            # Final update
            live.update(generate_layout())
            
        # Show summary
        total = len(instances)
        completed = sum(1 for s in self.instance_status.values() if "✓" in s["status"])
        failed = total - completed
        
        self.console.print("\n[bold]Destruction Summary:[/bold]")
        if completed == total:
            self.console.print(f"[green]✅ All {total} instances destroyed successfully[/green]")
        else:
            self.console.print(f"[yellow]⚠️  {completed}/{total} instances destroyed[/yellow]")
            if failed > 0:
                self.console.print(f"[red]❌ {failed} instances failed[/red]")
                
        self.console.print(f"\n[dim]Destruction log saved to: {log_filename}[/dim]")


def cmd_destroy(config: SimpleConfig, state: SimpleStateManager) -> None:
    """Destroy all instances with enhanced UI."""
    if not check_aws_auth():
        return
        
    console = Console()
    manager = DestroyManager(config, state, console)
    manager.run()