"""Setup command implementation."""

import os

import yaml

from ..core.config import SimpleConfig
from ..utils.display import console, rich_error, rich_success, rich_warning


def merge_configs(existing: dict, defaults: dict) -> dict:
    """Merge default config with existing config, preserving user values."""
    result = existing.copy()

    for key, value in defaults.items():
        if key not in result:
            result[key] = value
        elif isinstance(value, dict) and isinstance(result[key], dict):
            # Recursively merge nested dictionaries
            result[key] = merge_configs(result[key], value)

    return result


def cmd_setup(config: SimpleConfig) -> None:
    """Guide user through creating or updating config.yaml."""
    # Get the actual host paths (these will be mapped from Docker volumes)
    # When running in Docker:
    # - /app/config maps to ~/.spot-deployer/config
    # - /app/files maps to ~/.spot-deployer/files
    # - /app/output maps to ~/.spot-deployer/output

    # Determine if we're in Docker
    in_docker = os.path.exists("/.dockerenv")

    if in_docker:
        # Show host paths for user clarity
        host_base = "$HOME/.spot-deployer"
        host_config = f"{host_base}/config/config.yaml"
        host_files = f"{host_base}/files"
        host_output = f"{host_base}/output"
    else:
        # Running locally
        host_config = config.config_file
        host_files = config.files_directory()
        host_output = config.output_directory()

    # First ensure the directory structure exists
    files_dir = config.files_directory()
    output_dir = config.output_directory()

    # Create directories if they don't exist
    for dir_path, dir_name in [
        (files_dir, "files directory"),
        (output_dir, "output directory"),
    ]:
        if not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path, exist_ok=True)
                rich_success(f"Created {dir_name}: {dir_path}")
            except Exception as e:
                rich_error(f"Failed to create {dir_name}: {e}")
                return

    # Default configuration
    default_config = {
        "aws": {
            "total_instances": 3,
            "username": "ubuntu",
            "public_ssh_key_path": "~/.ssh/id_rsa.pub",
            "private_ssh_key_path": "~/.ssh/id_rsa",
            "files_directory": "files",
            "scripts_directory": "instance/scripts",
            "cloud_init_template": "instance/cloud-init/init-vm-template.yml",
            "startup_script": "instance/scripts/startup.py",
            "instance_storage_gb": 50,
            "tags": {"Project": "SpotDeployer"},
            "use_dedicated_vpc": True,  # Create isolated VPC per deployment
        },
        "regions": [
            {"us-west-2": {"image": "auto", "machine_type": "t3.medium"}},
            {"us-east-1": {"image": "auto", "machine_type": "t3.medium"}},
            {"eu-west-1": {"image": "auto", "machine_type": "t3.medium"}},
        ],
    }

    # Check if config exists and merge if it does
    if os.path.exists(config.config_file):
        try:
            with open(config.config_file, "r") as f:
                existing_config = yaml.safe_load(f) or {}

            # Merge configs, preserving user values
            merged_config = merge_configs(existing_config, default_config)

            # Check if any new fields were added
            if merged_config != existing_config:
                rich_warning(f"Updating config with new fields: {config.config_file}")
                final_config = merged_config
            else:
                rich_success(f"Config is up to date: {config.config_file}")
                final_config = existing_config
        except Exception as e:
            rich_error(f"Failed to read existing config: {e}")
            rich_warning("Creating new config with defaults")
            final_config = default_config
    else:
        rich_warning("No existing config found, creating new one")
        final_config = default_config

    try:
        with open(config.config_file, "w") as f:
            yaml.dump(final_config, f, default_flow_style=False, sort_keys=False)

        if final_config == default_config:
            rich_success(f"Created default config: {config.config_file}")
        else:
            rich_success(f"Updated config: {config.config_file}")

        if console:
            console.print(f"""
[bold yellow]ACTION REQUIRED:[/bold yellow] Please review and edit the config file with your AWS details.

[bold]Local paths on your system:[/bold]
Config location: {host_config}
Files directory: {host_files}
Output directory: {host_output}

[bold cyan]Files Directory ({host_files}):[/bold cyan]
This directory is where you place files to upload to your spot instances.
Files placed here will be copied to /opt/uploaded_files/ on each instance.

[bold]Required credential files for Bacalhau compute nodes:[/bold]
• {host_files}/orchestrator_endpoint
  Contents: NATS endpoint URL (e.g., nats://orchestrator.example.com:4222)
  
• {host_files}/orchestrator_token  
  Contents: Authentication token for the orchestrator

[bold]Output Directory ({host_output}):[/bold]
This directory contains:
• instances.json - Current deployment state and instance tracking
• deployment logs - Logs from instance creation and configuration

[bold]Next Steps:[/bold]
1. Edit {host_config} with your AWS settings
2. Add orchestrator credentials to {host_files}/
3. Run: spot-deployer create""")
    except Exception as e:
        rich_error(f"Failed to write config file: {e}")
