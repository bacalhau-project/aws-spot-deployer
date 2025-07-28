"""Version command implementation."""

import os
import subprocess

from ..utils.display import console
from ..version import __version__


def get_docker_info():
    """Get Docker container information if running in Docker."""
    docker_info = {}

    # Check if running in Docker
    if os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER"):
        # Try to get Docker image ID from environment or labels
        docker_info["container"] = "yes"

        # Get image ID if available
        image_id = os.environ.get("DOCKER_IMAGE_ID", "unknown")
        docker_info["image_id"] = image_id

        # Get image tag if available
        image_tag = os.environ.get("DOCKER_IMAGE_TAG", "unknown")
        docker_info["image_tag"] = image_tag

        # Try to get build info from Docker labels if available
        try:
            result = subprocess.run(
                ["cat", "/proc/self/cgroup"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0 and "docker" in result.stdout:
                docker_info["runtime"] = "docker"
            else:
                docker_info["runtime"] = "container"
        except Exception:
            docker_info["runtime"] = "container"
    else:
        docker_info["container"] = "no"
        docker_info["runtime"] = "host"

    return docker_info


def get_git_info():
    """Get detailed git information."""
    git_info = {}

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
        console.print(f"[bold]spot-deployer[/bold] version [cyan]{__version__}[/cyan]\n")

        # Docker information
        docker_info = get_docker_info()
        if docker_info["container"] == "yes":
            console.print("[bold]Docker Information:[/bold]")
            console.print("  Running in container: [green]Yes[/green]")
            if docker_info.get("image_id") != "unknown":
                console.print(f"  Image ID: [cyan]{docker_info['image_id']}[/cyan]")
            if docker_info.get("image_tag") != "unknown":
                console.print(f"  Image Tag: [cyan]{docker_info['image_tag']}[/cyan]")
            console.print(f"  Runtime: [cyan]{docker_info['runtime']}[/cyan]")
        else:
            console.print("[bold]Docker Information:[/bold]")
            console.print("  Running in container: [yellow]No[/yellow]")
            console.print(f"  Runtime: [cyan]{docker_info['runtime']}[/cyan]")

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
        print(f"spot-deployer version {__version__}")
