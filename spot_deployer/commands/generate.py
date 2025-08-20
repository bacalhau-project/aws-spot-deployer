#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pyyaml",
#     "rich",
# ]
# ///

"""Generate command for creating standard deployment structure."""

from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm

console = Console()

# Template for AWS configuration
CONFIG_TEMPLATE = """# Spot Deployer Configuration
# This file defines AWS settings for your deployment

aws:
  # Total number of instances to deploy
  total_instances: 1

  # SSH settings
  username: ubuntu
  ssh_key_name: YOUR-SSH-KEY-NAME  # REQUIRED: Replace with your AWS SSH key name

  # Directories (relative to .spot/)
  files_directory: "files"
  scripts_directory: "scripts"

# Region configuration
# You can specify multiple regions with different instance types
regions:
  - us-west-2:
      machine_type: t3.medium
      image: auto  # Auto-discovers latest Ubuntu 22.04
"""

# Template for deployment manifest
DEPLOYMENT_TEMPLATE = """# Deployment Manifest
# This file defines what gets deployed to your instances

version: 1

deployment:
  # System packages to install via apt
  packages:
    - curl
    - wget
    - git
    - python3
    - python3-pip

  # Scripts to run during setup
  scripts:
    - name: setup
      path: scripts/setup.sh
      order: 1
    - name: additional
      path: scripts/additional_commands.sh
      order: 2

  # Files to upload (source:destination:permissions)
  uploads:
    # Example: Upload all files from files/ directory
    # - source: files/
    #   dest: /opt/uploaded_files/
    #   permissions: "0644"

  # SystemD services to install and start
  services:
    # Example service configuration
    # - name: my-app
    #   file: services/my-app.service
    #   enabled: true
"""

# Template for main setup script
SETUP_SCRIPT_TEMPLATE = """#!/bin/bash
# Main setup script for your deployment
# This script runs after packages are installed

set -e  # Exit on error

echo "Starting deployment setup..."

# Add your setup commands here
# Examples:
# - Clone repositories
# - Install application dependencies
# - Configure environment
# - Build your application

# Example: Install Python requirements
# if [ -f /opt/uploaded_files/requirements.txt ]; then
#     pip3 install -r /opt/uploaded_files/requirements.txt
# fi

echo "Setup complete!"
"""

# Template for additional commands script
ADDITIONAL_COMMANDS_TEMPLATE = """#!/bin/bash
# Additional commands script
# This runs after the main setup script
# Leave empty if not needed

# Add any additional setup commands here
"""

# Template for example systemd service
SERVICE_TEMPLATE = """[Unit]
Description=My Application Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/myapp
ExecStart=/usr/bin/python3 /opt/myapp/app.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
"""

# Template for gitignore
GITIGNORE_TEMPLATE = """# Spot Deployer
.spot/files/orchestrator_*
.spot/files/credentials*
.spot/files/secrets*
*.key
*.pem
"""


def create_file(path: Path, content: str, skip_existing: bool = True) -> bool:
    """Create a file with the given content.

    Args:
        path: Path to create the file at
        content: Content to write to the file
        skip_existing: If True, skip files that already exist

    Returns:
        True if file was created, False if skipped
    """
    if path.exists() and skip_existing:
        console.print(f"  [yellow]↷[/yellow] Skipping {path} (already exists)")
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)

    # Make scripts executable
    if path.suffix == ".sh":
        path.chmod(0o755)

    console.print(f"  [green]✓[/green] Created {path}")
    return True


def generate_structure(base_dir: Path = Path.cwd()) -> None:
    """Generate the standard deployment structure.

    Args:
        base_dir: Base directory to create structure in
    """
    spot_dir = base_dir / ".spot"

    console.print("\n[bold blue]Generating Spot Deployer structure...[/bold blue]\n")

    # Create directory structure
    directories = [
        spot_dir,
        spot_dir / "scripts",
        spot_dir / "services",
        spot_dir / "configs",
        spot_dir / "files",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        if not any(directory.iterdir()) or directory == spot_dir:
            console.print(f"  [green]✓[/green] Created {directory}/")

    # Create files
    files_created = 0
    files_skipped = 0

    # Core configuration files
    if create_file(spot_dir / "config.yaml", CONFIG_TEMPLATE):
        files_created += 1
    else:
        files_skipped += 1

    if create_file(spot_dir / "deployment.yaml", DEPLOYMENT_TEMPLATE):
        files_created += 1
    else:
        files_skipped += 1

    # Scripts
    if create_file(spot_dir / "scripts" / "setup.sh", SETUP_SCRIPT_TEMPLATE):
        files_created += 1
    else:
        files_skipped += 1

    if create_file(spot_dir / "scripts" / "additional_commands.sh", ADDITIONAL_COMMANDS_TEMPLATE):
        files_created += 1
    else:
        files_skipped += 1

    # Example service (only if services dir is empty)
    if not any((spot_dir / "services").glob("*.service")):
        if create_file(spot_dir / "services" / "example.service.disabled", SERVICE_TEMPLATE):
            files_created += 1

    # Create placeholder in files directory
    readme_content = """# Files Directory

Place any files you want to upload to instances here.
They will be uploaded to /opt/uploaded_files/ by default.

For sensitive files like credentials, use appropriate permissions in deployment.yaml.
"""
    if create_file(spot_dir / "files" / "README.md", readme_content):
        files_created += 1
    else:
        files_skipped += 1

    # Update .gitignore if it exists
    gitignore_path = base_dir / ".gitignore"
    if gitignore_path.exists():
        gitignore_content = gitignore_path.read_text()
        if ".spot/files/orchestrator_" not in gitignore_content:
            with open(gitignore_path, "a") as f:
                f.write("\n" + GITIGNORE_TEMPLATE)
            console.print("  [green]✓[/green] Updated .gitignore")
    else:
        if create_file(gitignore_path, GITIGNORE_TEMPLATE):
            files_created += 1

    # Summary
    console.print("\n[bold green]✅ Generation complete![/bold green]")
    console.print(f"  Created: {files_created} files")
    if files_skipped > 0:
        console.print(f"  Skipped: {files_skipped} existing files")

    console.print("\n[bold]Next steps:[/bold]")
    console.print("1. Edit [cyan].spot/config.yaml[/cyan] and set your SSH key name")
    console.print("2. Edit [cyan].spot/deployment.yaml[/cyan] to define your deployment")
    console.print("3. Add your setup logic to [cyan].spot/scripts/setup.sh[/cyan]")
    console.print("4. Place any files to upload in [cyan].spot/files/[/cyan]")
    console.print("5. Run [green]spot create[/green] to deploy\n")


def main():
    """Main entry point for generate command."""
    try:
        # Check if .spot already exists
        spot_dir = Path.cwd() / ".spot"
        if spot_dir.exists():
            if not Confirm.ask(
                "\n[yellow]⚠️  .spot/ directory already exists.[/yellow] Continue and skip existing files?"
            ):
                console.print("[red]Generation cancelled.[/red]")
                return

        generate_structure()

    except KeyboardInterrupt:
        console.print("\n[red]Generation cancelled by user.[/red]")
    except Exception as e:
        console.print(f"[red]Error during generation: {e}[/red]")
        raise


if __name__ == "__main__":
    main()
