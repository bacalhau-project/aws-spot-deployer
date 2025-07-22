"""Help command implementation."""
from ..utils.display import RICH_AVAILABLE, Panel, console


def cmd_help() -> None:
    """Display a Rich help panel."""
    if RICH_AVAILABLE and console:
        help_text = """
[bold]AWS Spot Instance Deployer[/bold]

[bold]Usage:[/bold]
  [cyan]./deploy_spot.py [command][/cyan]

[bold]Commands:[/bold]
  [green]setup[/green]      - Create a default 'config.yaml' file.
  [green]create[/green]     - Create and deploy spot instances based on 'config.yaml'.
  [green]list[/green]       - List all currently managed instances from 'instances.json'.
  [green]destroy[/green]    - Terminate all managed instances and clean up resources.
  [green]help[/green]       - Show this help message.
"""
        console.print(Panel(help_text, title="Help", border_style="blue"))
    else:
        print("Usage: ./deploy_spot.py [setup|create|list|destroy|help]")
