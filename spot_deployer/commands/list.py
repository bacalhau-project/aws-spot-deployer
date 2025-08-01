"""List command implementation."""

from concurrent.futures import ThreadPoolExecutor

from ..core.state import SimpleStateManager
from ..utils.aws import check_aws_auth
from ..utils.display import RICH_AVAILABLE, console, rich_print
from ..utils.tables import add_instance_row, create_instance_table


def get_instance_state(instance_id: str, region: str) -> str:
    """Get current state of an instance from AWS."""
    try:
        from ..utils.aws_manager import AWSResourceManager

        aws_manager = AWSResourceManager(region)
        return aws_manager.get_instance_state(instance_id)
    except Exception:
        return "error"


def cmd_list(state: SimpleStateManager) -> None:
    """List running instances with live state from AWS."""
    if not check_aws_auth():
        return

    # Show we're checking state file
    rich_print("[dim]Checking local state file for instances...[/dim]")

    instances = state.load_instances()
    if not instances:
        rich_print("No instances found in state file.", style="yellow")
        return

    # Show what we found
    rich_print(f"[green]Found {len(instances)} instances in state file[/green]")

    # Group by region for summary
    instances_by_region = {}
    for instance in instances:
        region = instance["region"]
        if region not in instances_by_region:
            instances_by_region[region] = 0
        instances_by_region[region] += 1

    # Show summary by region
    for region, count in instances_by_region.items():
        rich_print(f"  • {region}: {count} instances")

    # Show status while fetching
    if RICH_AVAILABLE and console:
        console.print("\n[dim]Fetching current instance states from AWS...[/dim]")

    # Update instance states from AWS in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Create a mapping of futures to instances
        future_to_instance = {
            executor.submit(get_instance_state, inst["id"], inst["region"]): inst
            for inst in instances
        }

        # Update states as futures complete
        for future in future_to_instance:
            instance = future_to_instance[future]
            try:
                current_state = future.result()
                instance["state"] = current_state
            except Exception:
                instance["state"] = "error"

    if RICH_AVAILABLE and console:
        table = create_instance_table(title="Running Spot Instances")

        for inst in sorted(instances, key=lambda i: i.get("region", "")):
            instance_state = inst.get("state", "unknown")

            # Keep status display simple
            state_display = instance_state

            add_instance_row(
                table,
                inst.get("region", "unknown"),
                inst.get("id", "unknown"),
                state_display,
                inst.get("type", "unknown"),
                inst.get("public_ip", "N/A"),
                inst.get("created", "unknown"),
            )

        console.print(table)
    else:
        # Fallback to basic output
        print(f"\nTotal instances: {len(instances)}")
        for inst in instances:
            print(
                f"  {inst.get('region', 'unknown')}: "
                f"{inst.get('id', 'unknown')} "
                f"({inst.get('public_ip', 'no-ip')})"
            )
