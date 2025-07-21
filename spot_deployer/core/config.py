"""Configuration management for spot deployer."""

import os
from typing import Dict, List, Optional

import yaml


class SimpleConfig:
    """Enhanced configuration loader with full options support."""

    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = config_file
        self.data = self._load_config()

    def _load_config(self) -> Dict:
        """Load YAML configuration."""
        try:
            with open(self.config_file, "r") as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            print(f"Config file {self.config_file} not found. Run 'setup' first.")
            return {}
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}

    def regions(self) -> List[str]:
        """Get list of regions."""
        return [list(region.keys())[0] for region in self.data.get("regions", [])]

    def instance_count(self) -> int:
        """Get total instance count."""
        return self.data.get("aws", {}).get("total_instances", 3)

    def username(self) -> str:
        """Get SSH username."""
        return self.data.get("aws", {}).get("username", "ubuntu")

    def ssh_key_name(self) -> Optional[str]:
        """Get SSH key name if configured. (Deprecated - we use local SSH keys via cloud-init)"""
        return self.data.get("aws", {}).get("ssh_key_name")

    def public_ssh_key_path(self) -> Optional[str]:
        """Get public SSH key file path."""
        path = self.data.get("aws", {}).get("public_ssh_key_path")
        if path:
            return self._resolve_ssh_path(path)
        return None

    def private_ssh_key_path(self) -> Optional[str]:
        """Get private SSH key file path."""
        path = self.data.get("aws", {}).get("private_ssh_key_path")
        if path:
            return self._resolve_ssh_path(path)
        return None
    
    def _raw_public_ssh_key_path(self) -> Optional[str]:
        """Get raw public SSH key path from config (unresolved)."""
        return self.data.get("aws", {}).get("public_ssh_key_path")

    def _resolve_ssh_path(self, path: str) -> str:
        """Resolve SSH path for both local and container environments."""
        # If running in Docker container (detected by SPOT_CONFIG_PATH env var)
        if os.environ.get("SPOT_CONFIG_PATH"):
            # First expand any ~ references
            expanded_path = os.path.expanduser(path)
            
            # Extract just the .ssh part of the path
            if "/.ssh/" in expanded_path:
                ssh_part = expanded_path[expanded_path.index("/.ssh/"):]
                return f"/root{ssh_part}"
            elif expanded_path.endswith("/.ssh"):
                return "/root/.ssh"
            
            # Fallback mapping for other paths
            path_mappings = {
                "/Users/": "/root/",  # macOS home to container root
                "/home/": "/root/",   # Linux home to container root
            }
            
            for local_prefix, container_prefix in path_mappings.items():
                if expanded_path.startswith(local_prefix):
                    # Extract username and rest of path
                    remaining = expanded_path[len(local_prefix):]
                    if "/" in remaining:
                        # Skip the username part
                        rest = remaining[remaining.index("/"):]
                        return container_prefix + rest.lstrip("/")
                    else:
                        return container_prefix
        
        # For local execution, just expand user
        return os.path.expanduser(path)

    def public_ssh_key_content(self) -> Optional[str]:
        """Get public SSH key content."""
        key_path = self.public_ssh_key_path()  # Already resolved
        if key_path:
            if os.path.exists(key_path):
                try:
                    with open(key_path, "r") as f:
                        return f.read().strip()
                except Exception as e:
                    print(f"Error reading public key from {key_path}: {e}")
            else:
                print(f"❌ Public SSH key not found at '{key_path}'")
        return None

    def files_directory(self) -> str:
        """Get files directory path."""
        return self.data.get("aws", {}).get("files_directory", "files")

    def scripts_directory(self) -> str:
        """Get scripts directory path."""
        return self.data.get("aws", {}).get("scripts_directory", "instance/scripts")

    def cloud_init_template(self) -> str:
        """Get cloud-init template path."""
        return self.data.get("aws", {}).get(
            "cloud_init_template", "instance/cloud-init/init-vm-template.yml"
        )

    def startup_script(self) -> str:
        """Get startup script path."""
        return self.data.get("aws", {}).get(
            "startup_script", "instance/scripts/startup.py"
        )

    def additional_commands_script(self) -> Optional[str]:
        """Get additional commands script path."""
        return self.data.get("aws", {}).get("additional_commands_script")

    def bacalhau_data_dir(self) -> str:
        """Get Bacalhau data directory."""
        return self.data.get("aws", {}).get("bacalhau_data_dir", "/bacalhau_data")

    def bacalhau_node_dir(self) -> str:
        """Get Bacalhau node directory."""
        return self.data.get("aws", {}).get("bacalhau_node_dir", "/bacalhau_node")

    def bacalhau_config_template(self) -> str:
        """Get Bacalhau config template path."""
        return self.data.get("aws", {}).get(
            "bacalhau_config_template", "instance/config/bacalhau-config-template.yaml"
        )

    def docker_compose_template(self) -> str:
        """Get Docker Compose template path."""
        return self.data.get("aws", {}).get(
            "docker_compose_template", "instance/scripts/docker-compose.yaml"
        )

    def spot_price_limit(self) -> Optional[float]:
        """Get spot price limit."""
        return self.data.get("aws", {}).get("spot_price_limit")

    def instance_storage_gb(self) -> int:
        """Get instance storage size in GB."""
        return self.data.get("aws", {}).get("instance_storage_gb", 50)

    def security_group_name(self) -> str:
        """Get security group name."""
        return self.data.get("aws", {}).get("security_group_name", "spot-deployer-sg")

    def vpc_tag_name(self) -> Optional[str]:
        """Get VPC tag name for filtering."""
        return self.data.get("aws", {}).get("vpc_tag_name")

    def associate_public_ip(self) -> bool:
        """Whether to associate public IP addresses."""
        return self.data.get("aws", {}).get("associate_public_ip", True)

    def tags(self) -> Dict[str, str]:
        """Get additional tags for instances."""
        return self.data.get("aws", {}).get("tags", {})

    def use_dedicated_vpc(self) -> bool:
        """Whether to create dedicated VPCs for each deployment."""
        return self.data.get("aws", {}).get("use_dedicated_vpc", False)

    def ensure_default_vpc(self) -> bool:
        """Whether to create default VPCs if they don't exist."""
        return self.data.get("aws", {}).get("ensure_default_vpc", True)

    def region_config(self, region: str) -> Dict:
        """Get config for specific region."""
        for r in self.data.get("regions", []):
            if region in r:
                return r[region]
        return {"machine_type": "t3.medium", "image": "auto"}
