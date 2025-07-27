"""Setup command implementation."""

import os

import yaml

from ..core.config import SimpleConfig
from ..utils.display import console, rich_error, rich_success, rich_warning


def cmd_setup(config: SimpleConfig) -> None:
    """Guide user through creating a default config.yaml."""
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
        
        # Create a sample README in the files directory
        readme_path = os.path.join(files_dir, "README.txt")
        if not os.path.exists(readme_path):
            with open(readme_path, "w") as f:
                f.write("# Files Directory\n\n")
                f.write("Place files here that you want to upload to your spot instances.\n")
                f.write("These files will be copied to /opt/uploaded_files/ on each instance.\n\n")
                f.write("Required files for Bacalhau compute nodes:\n")
                f.write("- orchestrator_endpoint: Contains the NATS endpoint URL\n")
                f.write("- orchestrator_token: Contains the authentication token\n")
            rich_success("Created sample README in files directory")
        
        if console:
            console.print(
                "\n[bold yellow]ACTION REQUIRED:[/bold yellow] Please edit the config file with your details."
            )
            console.print(f"Config location: {config.config_file}")
            console.print(f"Files directory: {files_dir}")
            console.print(f"Output directory: {output_dir}")
    except Exception as e:
        rich_error(f"Failed to create config file: {e}")
