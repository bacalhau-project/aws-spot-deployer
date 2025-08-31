"""Version command implementation."""

import os
import subprocess
from typing import Any

from .._version import __version__
from ..utils.display import console


def get_runtime_info() -> dict[str, str]:
    """Get runtime environment information."""
    runtime_info = {}

    # Check if running via uvx
    if os.environ.get("UV_PROJECT_ROOT") or os.environ.get("UV_CACHE_DIR"):
        runtime_info["runtime"] = "uvx"
        runtime_info["container"] = "no"
    # Check if running in a container
    elif os.path.exists("/.dockerenv") or os.environ.get("RUNNING_IN_CONTAINER"):
        runtime_info["container"] = "yes"
        runtime_info["runtime"] = "container"
    else:
        runtime_info["container"] = "no"
        runtime_info["runtime"] = "host"

    return runtime_info


def get_git_info() -> dict[str, Any]:
    """Get detailed git information."""
    git_info: dict[str, Any] = {}

    try:
        # Get current branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            git_info["branch"] = result.stdout.strip()

        # Get full commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            git_info["commit"] = result.stdout.strip()

        # Get commit date
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ci"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            git_info["commit_date"] = result.stdout.strip()

        # Check if working directory is clean
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            git_info["dirty"] = len(result.stdout.strip()) > 0

    except Exception:
        pass

    return git_info


def cmd_version() -> None:
    """Display version information."""
    if console:
        console.print(f"[bold]amauo[/bold] version [cyan]{__version__}[/cyan]\n")

        # Runtime information
        runtime_info = get_runtime_info()
        console.print("[bold]Runtime Information:[/bold]")
        console.print(f"  Runtime: [cyan]{runtime_info['runtime']}[/cyan]")
        if runtime_info["container"] == "yes":
            console.print("  Running in container: [green]Yes[/green]")
        else:
            console.print("  Running in container: [yellow]No[/yellow]")

        # Git information
        git_info = get_git_info()
        if git_info:
            console.print("\n[bold]Git Information:[/bold]")
            if "branch" in git_info:
                console.print(f"  Branch: [cyan]{git_info['branch']}[/cyan]")
            if "commit" in git_info:
                console.print(f"  Commit: [cyan]{git_info['commit']}[/cyan]")
            if "commit_date" in git_info:
                console.print(f"  Commit Date: [cyan]{git_info['commit_date']}[/cyan]")
            if "dirty" in git_info:
                if git_info["dirty"]:
                    console.print("  Working Directory: [yellow]Modified[/yellow]")
                else:
                    console.print("  Working Directory: [green]Clean[/green]")

        # Build information (from environment variables that could be set during build)
        build_date = os.environ.get("BUILD_DATE")
        build_host = os.environ.get("BUILD_HOST")
        if build_date or build_host:
            console.print("\n[bold]Build Information:[/bold]")
            if build_date:
                console.print(f"  Build Date: [cyan]{build_date}[/cyan]")
            if build_host:
                console.print(f"  Build Host: [cyan]{build_host}[/cyan]")
    else:
        print(f"amauo version {__version__}")
