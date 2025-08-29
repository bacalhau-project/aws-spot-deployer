"""
Configuration adapter to handle transition from cluster.yaml to config.yaml format.

This module provides utilities to convert between SkyPilot cluster configuration
and SPAT-based configuration formats, enabling seamless migration.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class ConfigAdapter:
    """Adapts between cluster.yaml (SkyPilot) and config.yaml (SPAT) formats."""

    def __init__(self):
        self.cluster_config: Optional[Dict[str, Any]] = None
        self.spat_config: Optional[Dict[str, Any]] = None

    def load_cluster_config(self, cluster_file: str = "cluster.yaml") -> Dict[str, Any]:
        """Load SkyPilot cluster configuration."""
        cluster_path = Path(cluster_file)
        if not cluster_path.exists():
            raise FileNotFoundError(f"Cluster config not found: {cluster_file}")

        with open(cluster_path) as f:
            self.cluster_config = yaml.safe_load(f)
        
        return self.cluster_config

    def convert_to_spat_config(self, cluster_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Convert cluster.yaml format to config.yaml format."""
        if cluster_config is None:
            if self.cluster_config is None:
                raise ValueError("No cluster config loaded. Call load_cluster_config first.")
            cluster_config = self.cluster_config

        # Extract regions and resource info from SkyPilot config
        regions_config = []
        resources = cluster_config.get("resources", {})
        
        # Handle SkyPilot region specification
        cloud = resources.get("cloud", "aws")
        instance_type = resources.get("instance_type", "t3.medium")
        
        # Handle region mapping
        skypilot_regions = resources.get("region", ["us-west-2"])
        if isinstance(skypilot_regions, str):
            skypilot_regions = [skypilot_regions]

        for region in skypilot_regions:
            regions_config.append({
                region: {
                    "machine_type": instance_type,
                    "image": "auto"  # Auto-discover Ubuntu AMI
                }
            })

        # Extract other settings
        num_nodes = resources.get("num_nodes", 9)
        disk_size = resources.get("disk_size", 50)

        # Map SkyPilot setup commands to files/scripts
        setup_commands = cluster_config.get("setup", "")
        run_commands = cluster_config.get("run", "")

        # Build SPAT configuration
        spat_config = {
            "aws": {
                "total_instances": num_nodes,
                "username": "ubuntu",  # Default for Ubuntu AMIs
                "ssh_key_name": "",  # Will need to be filled in
                "public_ssh_key_path": "~/.ssh/id_rsa.pub",
                "private_ssh_key_path": "~/.ssh/id_rsa",
                "instance_storage_gb": disk_size,
                "use_dedicated_vpc": False
            },
            "regions": regions_config
        }

        # Add tags if present
        if "metadata" in cluster_config:
            spat_config["aws"]["tags"] = cluster_config["metadata"]

        self.spat_config = spat_config
        return spat_config

    def save_spat_config(self, config_file: str = "config.yaml", spat_config: Optional[Dict[str, Any]] = None) -> None:
        """Save SPAT configuration to config.yaml."""
        if spat_config is None:
            if self.spat_config is None:
                raise ValueError("No SPAT config available. Call convert_to_spat_config first.")
            spat_config = self.spat_config

        config_path = Path(config_file)
        
        # Create backup if file exists
        if config_path.exists():
            backup_path = config_path.with_suffix(f"{config_path.suffix}.backup")
            config_path.rename(backup_path)
            print(f"Backed up existing config to {backup_path}")

        with open(config_path, 'w') as f:
            # Write with comments for better user experience
            f.write("# Amauo Configuration (converted from cluster.yaml)\n")
            f.write("# This configuration manages Bacalhau compute nodes across cloud regions\n\n")
            yaml.dump(spat_config, f, default_flow_style=False, indent=2)

        print(f"Saved SPAT configuration to {config_file}")

    def create_deployment_structure(self, 
                                  setup_commands: Optional[str] = None, 
                                  run_commands: Optional[str] = None) -> None:
        """Create deployment structure based on SkyPilot commands."""
        deployment_dir = Path("deployment")
        deployment_dir.mkdir(exist_ok=True)

        # Create scripts directory
        scripts_dir = deployment_dir / "scripts"
        scripts_dir.mkdir(exist_ok=True)

        # Create setup.sh from SkyPilot setup commands
        if setup_commands:
            setup_script = scripts_dir / "setup.sh"
            with open(setup_script, 'w') as f:
                f.write("#!/bin/bash\n")
                f.write("# Converted from SkyPilot setup commands\n\n")
                f.write("set -e\n\n")
                
                # Handle both string and list formats
                if isinstance(setup_commands, str):
                    f.write(setup_commands)
                elif isinstance(setup_commands, list):
                    for cmd in setup_commands:
                        f.write(f"{cmd}\n")
                
            setup_script.chmod(0o755)
            print(f"Created setup script: {setup_script}")

        # Create run script from SkyPilot run commands
        if run_commands:
            run_script = scripts_dir / "run.sh"
            with open(run_script, 'w') as f:
                f.write("#!/bin/bash\n")
                f.write("# Converted from SkyPilot run commands\n\n")
                f.write("set -e\n\n")
                
                # Handle both string and list formats
                if isinstance(run_commands, str):
                    f.write(run_commands)
                elif isinstance(run_commands, list):
                    for cmd in run_commands:
                        f.write(f"{cmd}\n")
                
            run_script.chmod(0o755)
            print(f"Created run script: {run_script}")

        # Create basic deployment manifest
        manifest_file = deployment_dir / "manifest.yaml"
        manifest = {
            "name": "amauo-bacalhau-deployment",
            "description": "Converted from SkyPilot cluster configuration",
            "uploads": []
        }

        # Add scripts to uploads
        if setup_commands or run_commands:
            manifest["uploads"].append({
                "source": "scripts/",
                "destination": "/opt/deployment/scripts/",
                "permissions": "755"
            })

        with open(manifest_file, 'w') as f:
            yaml.dump(manifest, f, default_flow_style=False, indent=2)

        print(f"Created deployment manifest: {manifest_file}")

    def convert_full_migration(self, cluster_file: str = "cluster.yaml", config_file: str = "config.yaml") -> None:
        """Perform full migration from SkyPilot to SPAT format."""
        print(f"🔄 Converting {cluster_file} to SPAT format...")

        # Load and convert configuration
        cluster_config = self.load_cluster_config(cluster_file)
        spat_config = self.convert_to_spat_config(cluster_config)
        
        # Save SPAT config
        self.save_spat_config(config_file, spat_config)

        # Extract commands from cluster config
        setup_commands = cluster_config.get("setup")
        run_commands = cluster_config.get("run")

        # Create deployment structure if commands exist
        if setup_commands or run_commands:
            self.create_deployment_structure(setup_commands, run_commands)

        print("✅ Migration complete!")
        print(f"   • SPAT config: {config_file}")
        print(f"   • Deployment structure: deployment/")
        print(f"\nNext steps:")
        print(f"   1. Review and update SSH key paths in {config_file}")
        print(f"   2. Test deployment with: amauo create")
        print(f"   3. Original cluster.yaml backed up as cluster.yaml.backup")


def migrate_config(cluster_file: str = "cluster.yaml", config_file: str = "config.yaml") -> None:
    """Convenience function to migrate from cluster.yaml to config.yaml."""
    adapter = ConfigAdapter()
    adapter.convert_full_migration(cluster_file, config_file)


if __name__ == "__main__":
    # CLI interface for standalone usage
    import sys
    
    cluster_file = sys.argv[1] if len(sys.argv) > 1 else "cluster.yaml"
    config_file = sys.argv[2] if len(sys.argv) > 2 else "config.yaml"
    
    migrate_config(cluster_file, config_file)