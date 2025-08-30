"""Setup command implementation."""

import os

import yaml

from ..core.config import SimpleConfig
from ..utils.config_validator import ConfigValidator
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
    # When running via uvx, the config is in the current directory
    # So we always want to show paths relative to where the user is running the command

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
            "startup_script": "instance/scripts/deploy_services.py",
            "instance_storage_gb": 50,
            "tags": {"Project": "Amauo"},
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
            with open(config.config_file) as f:
                existing_config = yaml.safe_load(f) or {}

            # Merge configs, preserving user values
            merged_config = merge_configs(existing_config, default_config)

            # Check if any new fields were added
            if merged_config != existing_config:
                rich_warning("Updating config.yaml with new fields")
                final_config = merged_config
            else:
                rich_success("Config is up to date")
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
            rich_success("Created default config.yaml")
        else:
            rich_success("Updated config.yaml")

        # Validate the configuration
        validator = ConfigValidator()
        is_valid, _ = validator.validate_config_file(config.config_file)

        if not is_valid:
            console.print(
                "\n[bold red]Configuration has issues that need to be fixed:[/bold red]"
            )
            validator.suggest_fixes()

        if console:
            console.print("""
[bold yellow]ACTION REQUIRED:[/bold yellow] Please review and edit the config file with your AWS details.

[bold]Directory structure created in current directory:[/bold]
• config.yaml    - Your deployment configuration
• files/         - Place files here to upload to instances
• output/        - Deployment state and logs will be stored here

[bold cyan]Files Directory (./files):[/bold cyan]
This is where you place files to upload to your spot instances.
Files placed here will be copied to /opt/uploaded_files/ on each instance.

[bold]Required credential files for compute nodes:[/bold]
• files/orchestrator_endpoint
  Contents: NATS endpoint URL (e.g., nats://orchestrator.example.com:4222)

• files/orchestrator_token
  Contents: Authentication token for the orchestrator

[bold]Output Directory (./output):[/bold]
After deployment, this directory will contain:
• instances.json - Current deployment state and instance tracking
• deployment logs - Logs from instance creation and configuration

[bold]Next Steps:[/bold]
1. Edit config.yaml with your AWS settings
2. Add orchestrator credentials to files/
3. Run: amauo create""")
    except Exception as e:
        rich_error(f"Failed to write config file: {e}")
