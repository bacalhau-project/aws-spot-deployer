"""Help command implementation."""

from ..utils.display import RICH_AVAILABLE, Panel, console


def cmd_help() -> None:
    """Display a Rich help panel."""
    if RICH_AVAILABLE and console:
        help_text = """
[bold]Amauo - Deploy Bacalhau compute nodes effortlessly across the cloud[/bold]

[bold]Usage:[/bold]
  [cyan]amauo [command] [options][/cyan]

[bold]Commands:[/bold]
  [green]setup[/green]      - Create a default 'config.yaml' file and directory structure.
  [green]generate[/green]   - Generate standard deployment structure in current directory.
  [green]validate[/green]   - Validate deployment configuration before deployment.
  [green]create[/green]     - Create and deploy spot instances based on 'config.yaml'.
  [green]list[/green]       - List all currently managed instances from 'instances.json'.
  [green]destroy[/green]    - Terminate all managed instances and clean up resources.
  [green]nuke[/green]       - [red]DANGER:[/red] Find and destroy ALL spot instances in ALL regions.
  [green]random-ip[/green]  - Output a random instance IP address for SSH access.
  [green]readme[/green]     - Display information about the files directory and requirements.
  [green]help[/green]       - Show this help message.
  [green]version[/green]    - Show version information.

[bold]Options:[/bold]
  [yellow]--config, -c[/yellow]   - Path to config file (default: ./config.yaml)
  [yellow]--files, -f[/yellow]    - Path to files directory (default: ./instance-files/)
  [yellow]--output, -o[/yellow]   - Path to output directory (default: ./output/)
  [yellow]--verbose, -v[/yellow]  - Enable verbose output
  [yellow]--version, -V[/yellow]  - Show version

[bold]Environment Variables:[/bold]
  [blue]AMAUO_CONFIG[/blue]      - Override default config file path
  [blue]AMAUO_FILES[/blue]       - Override default files directory
  [blue]AMAUO_OUTPUT[/blue]      - Override default output directory
"""
        console.print(Panel(help_text, title="Help", border_style="blue"))
    else:
        print(
            "Usage: amauo [setup|generate|create|list|destroy|nuke|random-ip|readme|validate|help|version] [--config PATH]"
        )
