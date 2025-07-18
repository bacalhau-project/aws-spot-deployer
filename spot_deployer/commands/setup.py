"""Setup command implementation."""
import os
import yaml

from ..core.config import SimpleConfig
from ..utils.display import rich_warning, rich_success, rich_error, console


def cmd_setup(config: SimpleConfig) -> None:
    """Guide user through creating a default config.yaml."""
    if os.path.exists(config.config_file):
        rich_warning(f"'{config.config_file}' already exists.")
        if input("Overwrite? (y/n): ").lower() != "y":
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
    
    try:
        with open(config.config_file, "w") as f:
            yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)
        rich_success(f"Created default config: {config.config_file}")
        if console:
            console.print("\n[bold yellow]ACTION REQUIRED:[/bold yellow] Please edit this file with your details.")
    except Exception as e:
        rich_error(f"Failed to create config file: {e}")