#!/usr/bin/env uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "skypilot[aws]",
#     "rich",
# ]
# ///

"""
Install and verify SkyPilot for Bacalhau deployment.
"""

import subprocess
import sys

from rich.console import Console

console = Console()


def check_skypilot_installation():
    """Check if SkyPilot is properly installed and configured."""
    try:
        import sky

        console.print(f"[green]✓[/green] SkyPilot version: {sky.__version__}")
        return True
    except ImportError:
        console.print("[red]✗[/red] SkyPilot not available")
        return False


def check_aws_configuration():
    """Check AWS configuration for SkyPilot."""
    try:
        result = subprocess.run(["sky", "check", "aws"], capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            console.print("[green]✓[/green] AWS configuration valid")
            return True
        else:
            console.print(f"[red]✗[/red] AWS check failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        console.print("[red]✗[/red] AWS check timed out")
        return False
    except Exception as e:
        console.print(f"[red]✗[/red] AWS check error: {e}")
        return False


def check_supported_clouds():
    """Check what clouds are supported."""
    try:
        result = subprocess.run(["sky", "check"], capture_output=True, text=True, timeout=60)

        console.print("\n[bold]Cloud Provider Status:[/bold]")

        # Parse the output to show cloud status
        lines = result.stdout.split("\n")
        for line in lines:
            if "enabled" in line.lower():
                console.print(f"[green]✓[/green] {line.strip()}")
            elif "disabled" in line.lower():
                console.print(f"[red]✗[/red] {line.strip()}")

        return True

    except Exception as e:
        console.print(f"[red]✗[/red] Cloud check error: {e}")
        return False


def main():
    """Main installation and verification routine."""
    console.print("[bold blue]SkyPilot Installation and Verification[/bold blue]\n")

    # Check SkyPilot installation
    if not check_skypilot_installation():
        console.print("[red]Failed to import SkyPilot. Installation may have failed.[/red]")
        return 1

    # Check AWS configuration specifically
    aws_ok = check_aws_configuration()

    # Check all cloud providers
    check_supported_clouds()

    # Summary
    console.print("\n[bold]Summary:[/bold]")
    if aws_ok:
        console.print("[green]✓[/green] SkyPilot is ready for AWS spot deployments")
        console.print("\n[bold]Next steps:[/bold]")
        console.print("1. Create SkyPilot task YAML files")
        console.print("2. Set up deployment staging directories")
        console.print("3. Configure Bacalhau credentials")
        return 0
    else:
        console.print("[red]✗[/red] AWS configuration issues detected")
        console.print("\n[bold]Required actions:[/bold]")
        console.print("1. Run: aws configure")
        console.print("2. Ensure AWS credentials are valid")
        console.print("3. Check AWS permissions for EC2, VPC, etc.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
