"""
Command-line interface for spot-deployer.

Provides a Click-based CLI for deploying and managing SkyPilot clusters.
"""

import sys
from pathlib import Path

import click
from rich.console import Console

from . import get_runtime_version
from .manager import ClusterManager

console = Console()


@click.group(invoke_without_command=True)
@click.option(
    "-c",
    "--config",
    default="cluster.yaml",
    help="Config file path",
    show_default=True,
)
@click.option(
    "-f",
    "--console",
    is_flag=True,
    help="Show logs to console instead of log file",
)
@click.option(
    "--log-file",
    default="cluster-deploy.log",
    help="Log file path",
    show_default=True,
)
@click.option(
    "--version",
    is_flag=True,
    help="Show version and exit",
)
@click.pass_context
def cli(
    ctx: click.Context,
    config: str,
    console: bool,
    log_file: str,
    version: bool,
) -> None:
    """
    🌟 Amauo - Deploy clusters effortlessly across the cloud.

    Deploy Bacalhau compute nodes across multiple cloud regions using SkyPilot
    for cloud orchestration and spot instance management.

    Examples:
        uvx amauo create              # Deploy cluster
        uvx amauo status              # Check status
        uvx amauo list                # List nodes
        uvx amauo destroy             # Clean up
    """
    if version:
        runtime_version = get_runtime_version()
        click.echo(f"amauo version {runtime_version}")
        sys.exit(0)

    # Store common options in context
    ctx.ensure_object(dict)
    ctx.obj["config"] = config
    ctx.obj["console"] = console
    ctx.obj["log_file"] = log_file
    ctx.obj["manager"] = ClusterManager(log_to_console=console, log_file=log_file)

    # Show help if no command provided
    if ctx.invoked_subcommand is None:
        runtime_version = get_runtime_version()
        click.echo(f"Amauo v{runtime_version}")
        click.echo(ctx.get_help())


@cli.command()
@click.pass_context
def create(ctx: click.Context) -> None:
    """Deploy a global cluster across multiple regions."""
    manager: ClusterManager = ctx.obj["manager"]
    config_file: str = ctx.obj["config"]

    if not Path(config_file).exists():
        console.print(f"[red]❌ Config file not found: {config_file}[/red]")
        console.print(
            f"[yellow]Create {config_file} or use -c to specify a different file[/yellow]"
        )
        sys.exit(1)

    runtime_version = get_runtime_version()
    console.print(f"[blue]Amauo v{runtime_version}[/blue]")

    if not manager.check_prerequisites():
        sys.exit(1)

    if not manager.deploy_cluster(config_file):
        sys.exit(1)


@cli.command()
@click.pass_context
def destroy(ctx: click.Context) -> None:
    """Destroy the cluster and clean up all resources."""
    manager: ClusterManager = ctx.obj["manager"]

    runtime_version = get_runtime_version()
    console.print(f"[blue]Amauo v{runtime_version}[/blue]")

    if not manager.destroy_cluster():
        sys.exit(1)


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show cluster status and resource information."""
    manager: ClusterManager = ctx.obj["manager"]

    runtime_version = get_runtime_version()
    console.print(f"[blue]Amauo v{runtime_version}[/blue]")

    if not manager.check_prerequisites():
        sys.exit(1)

    if not manager.show_status():
        sys.exit(1)


@cli.command(name="list")
@click.pass_context
def list_nodes(ctx: click.Context) -> None:
    """List all nodes in the cluster with detailed information."""
    manager: ClusterManager = ctx.obj["manager"]

    runtime_version = get_runtime_version()
    console.print(f"[blue]Amauo v{runtime_version}[/blue]")

    if not manager.check_prerequisites():
        sys.exit(1)

    if not manager.list_nodes():
        sys.exit(1)


@cli.command()
@click.pass_context
def ssh(ctx: click.Context) -> None:
    """SSH into the cluster head node."""
    manager: ClusterManager = ctx.obj["manager"]

    runtime_version = get_runtime_version()
    console.print(f"[blue]Amauo v{runtime_version}[/blue]")

    if not manager.check_prerequisites():
        sys.exit(1)

    if not manager.ssh_cluster():
        sys.exit(1)


@cli.command()
@click.pass_context
def logs(ctx: click.Context) -> None:
    """Show cluster deployment and runtime logs."""
    manager: ClusterManager = ctx.obj["manager"]

    runtime_version = get_runtime_version()
    console.print(f"[blue]Amauo v{runtime_version}[/blue]")

    if not manager.check_prerequisites():
        sys.exit(1)

    if not manager.show_logs():
        sys.exit(1)


@cli.command()
@click.pass_context
def cleanup(ctx: click.Context) -> None:
    """Clean up Docker containers and local resources."""
    manager: ClusterManager = ctx.obj["manager"]

    runtime_version = get_runtime_version()
    console.print(f"[blue]Amauo v{runtime_version}[/blue]")
    manager.cleanup_docker()


@cli.command()
@click.pass_context
def check(ctx: click.Context) -> None:
    """Check prerequisites and system configuration."""
    manager: ClusterManager = ctx.obj["manager"]

    runtime_version = get_runtime_version()
    console.print(f"[blue]Amauo v{runtime_version}[/blue]")

    if not manager.check_prerequisites():
        sys.exit(1)

    console.print("[green]✅ All prerequisites satisfied![/green]")


def main() -> None:
    """Entry point for the CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
