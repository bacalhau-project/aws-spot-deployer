"""List command implementation."""
from ..core.state import SimpleStateManager
from ..utils.display import rich_print, RICH_AVAILABLE, console, Table


def cmd_list(state: SimpleStateManager) -> None:
    """List running instances from state file."""
    instances = state.load_instances()
    if not instances:
        rich_print("No instances found in state file.", style="yellow")
        return
    
    if RICH_AVAILABLE and console:
        table = Table(title="Running Spot Instances")
        table.add_column("Region", style="magenta")
        table.add_column("Instance ID", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Public IP", style="blue")
        table.add_column("State", style="yellow")
        table.add_column("Created", style="dim")
        
        for inst in sorted(instances, key=lambda i: i.get("region", "")):
            table.add_row(
                inst.get("region", "unknown"),
                inst.get("id", "unknown"),
                inst.get("type", "unknown"),
                inst.get("public_ip", "N/A"),
                inst.get("state", "unknown"),
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