"""Destroy command implementation with enhanced UI."""
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import boto3

from ..core.config import SimpleConfig
from ..core.state import SimpleStateManager
from ..utils.aws import check_aws_auth
from ..utils.display import (
    rich_warning, console, Table, Layout, Live, Panel
)
from ..utils.logging import setup_logger


def cmd_destroy(config: SimpleConfig, state: SimpleStateManager) -> None:
    """Terminate running instances and clean up resources with enhanced UI."""
    if not check_aws_auth():
        return
    
    instances = state.load_instances()
    if not instances:
        rich_warning("No instances to destroy.")
        return
    
    # Setup local logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"spot_destroy_{timestamp}.log"
    logger = setup_logger("spot_destroyer", log_filename)
    
    console.print(f"\n[bold red]⚠️  WARNING: This will terminate {len(instances)} instances[/bold red]")
    console.print("\nThe following instances will be terminated:")
    
    # Show instances to be destroyed
    destroy_table = Table(show_header=True, header_style="bold red")
    destroy_table.add_column("Region", style="magenta")
    destroy_table.add_column("Instance ID", style="cyan")
    destroy_table.add_column("Type", style="green")
    destroy_table.add_column("Public IP", style="blue")
    
    for inst in sorted(instances, key=lambda i: i.get("region", "")):
        destroy_table.add_row(
            inst.get("region", "unknown"),
            inst.get("id", "unknown"),
            inst.get("type", "unknown"),
            inst.get("public_ip", "N/A")
        )
    
    console.print(destroy_table)
    console.print("\n[yellow]This action cannot be undone![/yellow]")
    
    if input("\nType 'yes' to confirm destruction: ").lower() != "yes":
        console.print("[green]Destruction cancelled.[/green]")
        return
    
    # Group instances by region
    region_map = {}
    for inst in instances:
        region = inst.get("region")
        if region not in region_map:
            region_map[region] = []
        region_map[region].append(inst["id"])
    
    # Track destruction status
    destruction_status = {}
    for region, instance_ids in region_map.items():
        for inst_id in instance_ids:
            destruction_status[f"{region}-{inst_id}"] = {
                "region": region,
                "instance_id": inst_id,
                "status": "Pending",
                "security_group": "Pending"
            }
    
    def generate_destroy_layout():
        table = Table(
            title=f"Destroying {len(instances)} instances",
            show_header=True,
            header_style="bold red"
        )
        table.add_column("Region", style="magenta")
        table.add_column("Instance ID", style="cyan")
        table.add_column("Termination Status", style="yellow")
        table.add_column("Security Group", style="blue")
        
        for key, item in sorted(destruction_status.items()):
            status = item["status"]
            if "SUCCESS" in status or "terminated" in status.lower():
                status_style = f"[bold green]{status}[/bold green]"
            elif "ERROR" in status or "FAIL" in status:
                status_style = f"[bold red]{status}[/bold red]"
            else:
                status_style = f"[yellow]{status}[/yellow]"
            
            sg_status = item["security_group"]
            if "deleted" in sg_status.lower() or "cleaned" in sg_status.lower():
                sg_style = f"[green]{sg_status}[/green]"
            elif "error" in sg_status.lower() or "failed" in sg_status.lower():
                sg_style = f"[red]{sg_status}[/red]"
            else:
                sg_style = f"[yellow]{sg_status}[/yellow]"
            
            table.add_row(
                item["region"],
                item["instance_id"],
                status_style,
                sg_style
            )
        
        # Add log panel
        try:
            with open(log_filename, 'r') as f:
                log_content = "\n".join(f.readlines()[-10:])
        except (FileNotFoundError, IOError):
            log_content = "Waiting for log entries..."
        
        log_panel = Panel(log_content, title="Destruction Log", border_style="red", height=10)
        
        layout = Layout()
        layout.split_column(Layout(table), Layout(log_panel))
        return layout
    
    def update_status(region, instance_id, status=None, sg_status=None):
        key = f"{region}-{instance_id}"
        if key in destruction_status:
            if status:
                destruction_status[key]["status"] = status
            if sg_status:
                destruction_status[key]["security_group"] = sg_status
            logger.info(f"[{instance_id}] {status or ''} {sg_status or ''}")
    
    # Terminate instances and security groups
    def terminate_in_region(region, instance_ids):
        try:
            ec2 = boto3.client("ec2", region_name=region)
            
            # Update status for each instance
            for inst_id in instance_ids:
                update_status(region, inst_id, "Terminating...")
            
            # Terminate instances
            ec2.terminate_instances(InstanceIds=instance_ids)
            
            for inst_id in instance_ids:
                update_status(region, inst_id, "Termination requested")
            
            # Wait for instances to terminate
            logger.info(f"Waiting for {len(instance_ids)} instances to terminate in {region}...")
            waiter = ec2.get_waiter('instance_terminated')
            waiter.wait(
                InstanceIds=instance_ids,
                WaiterConfig={
                    'Delay': 5,
                    'MaxAttempts': 120  # 10 minutes max
                }
            )
            
            for inst_id in instance_ids:
                update_status(region, inst_id, "Terminated")
            
            # Get VPC for the security group
            vpcs = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])
            if not vpcs["Vpcs"]:
                # No default VPC, try to find security group by name
                try:
                    sgs = ec2.describe_security_groups(
                        Filters=[{"Name": "group-name", "Values": ["spot-deployer-sg"]}]
                    )
                    if sgs["SecurityGroups"]:
                        vpc_id = sgs["SecurityGroups"][0]["VpcId"]
                    else:
                        for inst_id in instance_ids:
                            update_status(region, inst_id, sg_status="No VPC found")
                        return region
                except ec2.exceptions.ClientError:
                    for inst_id in instance_ids:
                        update_status(region, inst_id, sg_status="No VPC found")
                    return region
            else:
                vpc_id = vpcs["Vpcs"][0]["VpcId"]
            
            # Delete security group with retry logic
            max_retries = 5
            retry_delay = 10
            
            for attempt in range(max_retries):
                try:
                    # Find security group
                    sgs = ec2.describe_security_groups(
                        Filters=[
                            {"Name": "vpc-id", "Values": [vpc_id]},
                            {"Name": "group-name", "Values": ["spot-deployer-sg"]}
                        ]
                    )
                    
                    if not sgs["SecurityGroups"]:
                        for inst_id in instance_ids:
                            update_status(region, inst_id, sg_status="SG not found")
                        break
                    
                    sg_id = sgs["SecurityGroups"][0]["GroupId"]
                    
                    # Check for dependencies
                    # Get all network interfaces using this security group
                    enis = ec2.describe_network_interfaces(
                        Filters=[{"Name": "group-id", "Values": [sg_id]}]
                    )
                    
                    if enis["NetworkInterfaces"]:
                        logger.warning(f"Security group {sg_id} still has {len(enis['NetworkInterfaces'])} network interfaces attached")
                        if attempt < max_retries - 1:
                            for inst_id in instance_ids:
                                update_status(region, inst_id, sg_status=f"Waiting for dependencies ({attempt+1}/{max_retries})")
                            time.sleep(retry_delay)
                            continue
                        else:
                            for inst_id in instance_ids:
                                update_status(region, inst_id, sg_status="Dependencies remain")
                            break
                    
                    # Try to delete the security group
                    ec2.delete_security_group(GroupId=sg_id)
                    for inst_id in instance_ids:
                        update_status(region, inst_id, sg_status="SG deleted")
                    logger.info(f"Security group {sg_id} deleted in {region}")
                    break
                    
                except ec2.exceptions.ClientError as e:
                    error_code = e.response['Error']['Code']
                    if error_code == 'InvalidGroup.NotFound':
                        for inst_id in instance_ids:
                            update_status(region, inst_id, sg_status="SG already deleted")
                        break
                    elif error_code == 'DependencyViolation':
                        if attempt < max_retries - 1:
                            for inst_id in instance_ids:
                                update_status(region, inst_id, sg_status=f"Retrying ({attempt+1}/{max_retries})")
                            logger.warning(f"Security group has dependencies, retrying in {retry_delay}s...")
                            time.sleep(retry_delay)
                        else:
                            for inst_id in instance_ids:
                                update_status(region, inst_id, sg_status="Failed: Dependencies")
                            logger.error(f"Failed to delete security group after {max_retries} attempts: {e}")
                    elif error_code == 'VPCIdNotSpecified':
                        for inst_id in instance_ids:
                            update_status(region, inst_id, sg_status="No default VPC")
                        logger.error(f"No default VPC in {region}")
                        break
                    else:
                        for inst_id in instance_ids:
                            update_status(region, inst_id, sg_status=f"Error: {error_code}")
                        logger.error(f"Failed to delete security group: {e}")
                        break
            
            return region
            
        except Exception as e:
            logger.error(f"Failed to terminate instances in {region}: {e}")
            for inst_id in instance_ids:
                update_status(region, inst_id, f"ERROR: {str(e)[:30]}", "Failed")
            return None
    
    with Live(generate_destroy_layout(), refresh_per_second=2, console=console) as live:
        with ThreadPoolExecutor(max_workers=len(region_map)) as executor:
            futures = [
                executor.submit(terminate_in_region, r, ids)
                for r, ids in region_map.items()
            ]
            
            # Wait for all terminations to complete with live updates
            while any(not f.done() for f in futures):
                live.update(generate_destroy_layout())
                time.sleep(0.5)
            
            # Final update
            live.update(generate_destroy_layout())
            
            # Process results
            for future in futures:
                terminated_region = future.result()
                if terminated_region:
                    state.remove_instances_by_region(terminated_region)
        
        # Keep display for a moment to show final status
        time.sleep(2)
    
    # Final summary
    console.print("\n[bold]Destruction Summary:[/bold]")
    success_count = sum(1 for s in destruction_status.values() if "Terminated" in s["status"])
    sg_success = sum(1 for s in destruction_status.values() if "deleted" in s["security_group"].lower())
    
    if success_count == len(instances):
        console.print(f"[green]✅ All {success_count} instances terminated successfully[/green]")
    else:
        console.print(f"[yellow]⚠️  {success_count}/{len(instances)} instances terminated[/yellow]")
    
    if sg_success > 0:
        console.print(f"[green]✅ {sg_success} security groups cleaned up[/green]")
    
    console.print(f"\n[dim]Destruction log saved to: {log_filename}[/dim]")