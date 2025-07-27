"""Help command implementation."""

from ..utils.display import RICH_AVAILABLE, Panel, console


def cmd_help() -> None:
    """Display a Rich help panel."""
    if RICH_AVAILABLE and console:
        help_text = """
[bold]AWS Spot Instance Deployer[/bold]

[bold]Usage:[/bold]
  [cyan]./deploy_spot.py [command] [options][/cyan]

[bold]Commands:[/bold]
  [green]setup[/green]      - Create a default 'config.yaml' file and directory structure.
  [green]create[/green]     - Create and deploy spot instances based on 'config.yaml'.
  [green]list[/green]       - List all currently managed instances from 'instances.json'.
  [green]destroy[/green]    - Terminate all managed instances and clean up resources.
  [green]help[/green]       - Show this help message.
  [green]version[/green]    - Show version information.

[bold]Options:[/bold]
  [yellow]--config, -c[/yellow]   - Path to config file (default: ./config.yaml)
  [yellow]--files, -f[/yellow]    - Path to files directory (default: ./files/)
  [yellow]--output, -o[/yellow]   - Path to output directory (default: ./output/)
  [yellow]--verbose, -v[/yellow]  - Enable verbose output
  [yellow]--version, -V[/yellow]  - Show version

[bold]Environment Variables:[/bold]
  [blue]SPOT_CONFIG[/blue]      - Override default config file path
  [blue]SPOT_FILES[/blue]       - Override default files directory
  [blue]SPOT_OUTPUT[/blue]      - Override default output directory
  [blue]SPOT_CONFIG_PATH[/blue] - Legacy: Override config file path
  [blue]SPOT_FILES_DIR[/blue]   - Legacy: Override files directory
  [blue]SPOT_OUTPUT_DIR[/blue]  - Legacy: Override output directory
"""
        console.print(Panel(help_text, title="Help", border_style="blue"))
    else:
        print(
            "Usage: ./deploy_spot.py [setup|create|list|destroy|help] [--config PATH] [--files PATH] [--output PATH]"
        )
