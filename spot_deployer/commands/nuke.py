"""Nuke command - finds and destroys ALL spot instances across all regions."""

from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

from botocore.exceptions import ClientError

from ..core.config import SimpleConfig
from ..core.state import SimpleStateManager
from ..utils.aws import check_aws_auth
from ..utils.display import console, rich_success

# AWS regions to scan
AWS_REGIONS = [
    "us-east-1",
    "us-east-2",
    "us-west-1",
    "us-west-2",
    "eu-west-1",
    "eu-west-2",
    "eu-west-3",
    "eu-central-1",
    "eu-north-1",
    "ap-northeast-1",
    "ap-northeast-2",
    "ap-northeast-3",
    "ap-southeast-1",
    "ap-southeast-2",
    "ap-south-1",
    "ca-central-1",
    "sa-east-1",
    "me-south-1",
    "af-south-1",
    "ap-east-1",
]


def find_spot_instances_in_region(region: str) -> List[Dict[str, Any]]:
    """Find all spot instances in a specific region."""
    try:
        from ..utils.aws_manager import AWSResourceManager

        aws_manager = AWSResourceManager(region)
        ec2 = aws_manager.ec2

        # Find all instances with lifecycle=spot
        response = ec2.describe_instances(
            Filters=[
                {"Name": "instance-lifecycle", "Values": ["spot"]},
                {
                    "Name": "instance-state-name",
                    "Values": ["pending", "running", "stopping", "stopped"],
                },
            ]
        )

        instances: List[Dict[str, Any]] = []
        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                # Extract tags safely
                tags_dict: Dict[str, str] = {}
                for tag in instance.get("Tags", []):
                    if "Key" in tag and "Value" in tag:
                        tags_dict[tag["Key"]] = tag["Value"]

                instances.append(
                    {
                        "id": instance.get("InstanceId", "unknown"),
                        "region": region,
                        "state": instance.get("State", {}).get("Name", "unknown"),
                        "type": instance.get("InstanceType", "unknown"),
                        "public_ip": instance.get("PublicIpAddress", "N/A"),
                        "launch_time": str(instance.get("LaunchTime", "unknown")),
                        "tags": tags_dict,
                    }
                )

        return instances
    except ClientError as e:
        error_response = e.response
        if error_response and "Error" in error_response:
            error = error_response["Error"]
            if "Code" in error and error["Code"] == "UnauthorizedOperation":
                # Skip regions where we don't have access
                return []
        raise


def terminate_instances_in_region(region: str, instance_ids: List[str]) -> Dict[str, str]:
    """Terminate instances in a specific region."""
    if not instance_ids:
        return {}

    try:
        from ..utils.aws_manager import AWSResourceManager

        aws_manager = AWSResourceManager(region)
        ec2 = aws_manager.ec2

        # Terminate instances
        response = ec2.terminate_instances(InstanceIds=instance_ids)

        # Extract termination status
        results: Dict[str, str] = {}
        for inst in response.get("TerminatingInstances", []):
            instance_id = inst.get("InstanceId", "unknown")
            current_state = inst.get("CurrentState", {})
            state_name = current_state.get("Name", "unknown")
            results[instance_id] = state_name

        return results
    except Exception as e:
        # Return error status for all instances
        return {inst_id: f"ERROR: {str(e)}" for inst_id in instance_ids}


def cmd_nuke(state: SimpleStateManager, config: SimpleConfig) -> None:
    """Find and destroy ALL spot instances across all AWS regions."""
    if not check_aws_auth():
        return

    console.print("\n[bold red]🚨 NUCLEAR OPTION - DESTROY ALL SPOT INSTANCES 🚨[/bold red]\n")
    console.print("[yellow]This command will:[/yellow]")
    console.print("  • Scan ALL AWS regions for spot instances")
    console.print("  • Terminate ALL spot instances found")
    console.print("  • This includes instances NOT managed by this tool\n")

    # Phase 1: Scan all regions for spot instances
    console.print("\n[cyan]Phase 1: Scanning all AWS regions for spot instances...[/cyan]")
    console.print(f"[dim]Scanning {len(AWS_REGIONS)} regions in parallel...[/dim]\n")

    all_instances: List[Dict[str, Any]] = []
    region_errors: List[tuple[str, str]] = []
    completed_regions = 0

    with ThreadPoolExecutor(max_workers=10) as executor:
        # Submit all region scans
        scan_future_to_region: Dict[Future[List[Dict[str, Any]]], str] = {
            executor.submit(find_spot_instances_in_region, region): region for region in AWS_REGIONS
        }

        # Process results as they complete
        for future in as_completed(scan_future_to_region):
            region = scan_future_to_region[future]
            completed_regions += 1
            progress = f"[{completed_regions}/{len(AWS_REGIONS)}]"

            try:
                instances = future.result()
                if instances:
                    all_instances.extend(instances)
                    console.print(
                        f"  {progress} [green]✓[/green] {region}: Found {len(instances)} spot instances"
                    )
                else:
                    console.print(f"  {progress} [dim]✓[/dim] {region}: No spot instances")
            except Exception as e:
                region_errors.append((region, str(e)))
                console.print(f"  {progress} [red]✗[/red] {region}: Error - {str(e)}")

    if region_errors:
        console.print(f"\n[yellow]⚠️  Failed to scan {len(region_errors)} regions[/yellow]")

    if not all_instances:
        rich_success("No spot instances found in any region!")
        return

    # Display found instances
    console.print(f"\n[bold]Found {len(all_instances)} spot instances:[/bold]\n")

    # Group by region for display
    by_region: Dict[str, List[Dict[str, Any]]] = {}
    for inst in all_instances:
        region = inst["region"]
        if region not in by_region:
            by_region[region] = []
        by_region[region].append(inst)

    for region, instances in sorted(by_region.items()):
        console.print(f"\n[bold]{region}:[/bold]")
        for inst in instances:
            tags_str = ", ".join(f"{k}={v}" for k, v in inst["tags"].items() if k != "Name")
            name_tag = inst["tags"].get("Name", "")
            if name_tag:
                name_str = f" [cyan]({name_tag})[/cyan]"
            else:
                name_str = ""

            console.print(
                f"  • {inst['id']}{name_str} - {inst['type']} - "
                f"{inst['state']} - {inst['public_ip']} - "
                f"[dim]{inst['launch_time']}[/dim]"
            )
            if tags_str:
                console.print(f"    [dim]Tags: {tags_str}[/dim]")

    # Phase 2: Terminate all instances
    console.print(
        f"\n[bold red]🔥 Terminating {len(all_instances)} instances across all regions![/bold red]"
    )

    # Group instances by region for termination
    termination_groups: Dict[str, List[str]] = {}
    for inst in all_instances:
        region = inst["region"]
        if region not in termination_groups:
            termination_groups[region] = []
        termination_groups[region].append(inst["id"])

    console.print(f"[dim]Terminating instances in {len(termination_groups)} regions...[/dim]\n")

    terminated_count = 0
    failed_count = 0
    completed_terminations = 0

    with ThreadPoolExecutor(max_workers=10) as executor:
        # Submit termination requests
        terminate_future_to_region: Dict[Future[Dict[str, str]], str] = {
            executor.submit(terminate_instances_in_region, region, instance_ids): region
            for region, instance_ids in termination_groups.items()
        }

        # Process results
        for future in as_completed(terminate_future_to_region):
            region = terminate_future_to_region[future]
            completed_terminations += 1
            progress = f"[{completed_terminations}/{len(termination_groups)}]"

            try:
                results = future.result()
                success = sum(1 for status in results.values() if "ERROR" not in status)
                failed = len(results) - success

                terminated_count += success
                failed_count += failed

                if failed > 0:
                    console.print(
                        f"  {progress} [yellow]⚠[/yellow] {region}: {success} terminated, {failed} failed"
                    )
                    for inst_id, status in results.items():
                        if "ERROR" in status:
                            console.print(f"       [red]✗[/red] {inst_id}: {status}")
                else:
                    console.print(
                        f"  {progress} [green]✓[/green] {region}: {success} instances terminated"
                    )

            except Exception as e:
                console.print(f"  {progress} [red]✗[/red] {region}: Failed - {str(e)}")
                failed_count += len(termination_groups[region])

    # Summary
    console.print("\n" + "=" * 60)
    console.print("\n[bold]NUKE COMPLETE:[/bold]")
    console.print(f"  [green]✅ Terminated: {terminated_count} instances[/green]")
    if failed_count > 0:
        console.print(f"  [red]❌ Failed: {failed_count} instances[/red]")

    # Update local state to remove any terminated instances
    if terminated_count > 0:
        console.print("\n[dim]Updating local state...[/dim]")
        current_instances = state.load_instances()
        # Get all terminated instance IDs
        terminated_ids = {inst["id"] for inst in all_instances}
        remaining_instances = [
            inst for inst in current_instances if inst["id"] not in terminated_ids
        ]
        state.save_instances(remaining_instances)
        console.print("[dim]Local state updated.[/dim]")

    console.print("\n[bold green]🏁 Nuke operation completed![/bold green]\n")
