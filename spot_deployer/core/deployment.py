#!/usr/bin/env python3
"""Deployment configuration and validation for portable spot deployer."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


@dataclass
class DeploymentConfig:
    """Configuration for a deployment."""

    # Deployment manifest data
    version: int = 1
    packages: List[str] = field(default_factory=list)
    scripts: List[Dict[str, Any]] = field(default_factory=list)
    uploads: List[Dict[str, Any]] = field(default_factory=list)
    services: List[Dict[str, Any]] = field(default_factory=list)
    template: Optional[str] = None  # Optional template name or path
    tarball_url: Optional[str] = None  # Optional tarball URL or path

    # Paths to actual files
    spot_dir: Path = field(default_factory=Path)
    config_path: Path = field(default_factory=Path)
    deployment_path: Path = field(default_factory=Path)
    scripts_dir: Path = field(default_factory=Path)
    services_dir: Path = field(default_factory=Path)
    configs_dir: Path = field(default_factory=Path)
    files_dir: Path = field(default_factory=Path)

    @classmethod
    def from_spot_dir(cls, spot_dir: Path) -> "DeploymentConfig":
        """Load deployment configuration from .spot directory.

        Args:
            spot_dir: Path to .spot directory

        Returns:
            DeploymentConfig instance

        Raises:
            FileNotFoundError: If required files are missing
            ValueError: If configuration is invalid
        """
        config = cls()
        config.spot_dir = spot_dir

        # Set paths
        config.config_path = spot_dir / "config.yaml"
        config.deployment_path = spot_dir / "deployment.yaml"
        config.scripts_dir = spot_dir / "scripts"
        config.services_dir = spot_dir / "services"
        config.configs_dir = spot_dir / "configs"
        config.files_dir = spot_dir / "files"

        # Load deployment manifest
        if not config.deployment_path.exists():
            raise FileNotFoundError(f"Deployment manifest not found: {config.deployment_path}")

        with open(config.deployment_path) as f:
            manifest = yaml.safe_load(f)

        # Parse manifest
        if manifest is None:
            manifest = {}

        config.version = manifest.get("version", 1)
        deployment = manifest.get("deployment", {})

        if deployment is None:
            deployment = {}

        config.packages = deployment.get("packages", []) or []
        config.scripts = deployment.get("scripts", []) or []
        config.uploads = deployment.get("uploads", []) or []
        config.services = deployment.get("services", []) or []
        config.template = deployment.get("template", None)
        config.tarball_url = deployment.get("tarball_url", None)

        return config

    def validate(self) -> Tuple[bool, List[str]]:
        """Validate the deployment configuration.

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check required directories exist
        if not self.spot_dir.exists():
            errors.append(f"Missing .spot directory: {self.spot_dir}")
            return False, errors

        if not self.config_path.exists():
            errors.append(f"Missing config.yaml: {self.config_path}")

        if not self.deployment_path.exists():
            errors.append(f"Missing deployment.yaml: {self.deployment_path}")

        # Check referenced scripts exist
        for script in self.scripts:
            script_path = self.spot_dir / script.get("path", "")
            if not script_path.exists():
                errors.append(f"Script not found: {script_path}")

        # Check referenced services exist
        for service in self.services:
            service_file = service.get("file", "")
            if service_file:
                service_path = self.spot_dir / service_file
                if not service_path.exists():
                    errors.append(f"Service file not found: {service_path}")

        # Check upload sources exist
        for upload in self.uploads:
            source = upload.get("source", "")
            if source:
                source_path = self.spot_dir / source
                if not source_path.exists():
                    errors.append(f"Upload source not found: {source_path}")

        # Validate config.yaml structure
        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    config = yaml.safe_load(f)

                # Check required fields
                if not config.get("aws"):
                    errors.append("config.yaml missing 'aws' section")
                elif not config["aws"].get("ssh_key_name"):
                    errors.append("config.yaml missing 'aws.ssh_key_name'")

                if not config.get("regions"):
                    errors.append("config.yaml missing 'regions' section")

            except yaml.YAMLError as e:
                errors.append(f"Invalid YAML in config.yaml: {e}")

        return len(errors) == 0, errors

    def get_all_files(self) -> List[Path]:
        """Get all files that need to be uploaded.

        Returns:
            List of file paths relative to spot_dir
        """
        files = []

        # Add scripts
        for script in self.scripts:
            script_path = Path(script.get("path", ""))
            if script_path:
                files.append(script_path)

        # Add service files
        for service in self.services:
            service_file = service.get("file", "")
            if service_file:
                files.append(Path(service_file))

        # Add upload sources
        for upload in self.uploads:
            source = upload.get("source", "")
            if source:
                source_path = self.spot_dir / source
                if source_path.is_file():
                    files.append(Path(source))
                elif source_path.is_dir():
                    # Add all files in directory
                    for file_path in source_path.rglob("*"):
                        if file_path.is_file():
                            rel_path = file_path.relative_to(self.spot_dir)
                            files.append(rel_path)

        return files


class DeploymentValidator:
    """Validates deployment structure and configuration."""

    @staticmethod
    def check_spot_directory(base_dir: Optional[Path] = None) -> Tuple[bool, List[str]]:
        """Check if .spot directory exists and has required structure.

        Args:
            base_dir: Base directory to check (defaults to cwd)

        Returns:
            Tuple of (is_valid, missing_items)
        """
        if base_dir is None:
            base_dir = Path.cwd()

        missing = []

        # Required files
        required_files = [
            ".spot/config.yaml",
            ".spot/deployment.yaml",
            ".spot/scripts/setup.sh",
            ".spot/scripts/additional_commands.sh",
        ]

        # Required directories
        required_dirs = [
            ".spot",
            ".spot/scripts",
            ".spot/services",
            ".spot/configs",
            ".spot/files",
        ]

        for dir_path in required_dirs:
            full_path = base_dir / dir_path
            if not full_path.exists() or not full_path.is_dir():
                missing.append(dir_path)

        for file_path in required_files:
            full_path = base_dir / file_path
            if not full_path.exists() or not full_path.is_file():
                missing.append(file_path)

        return len(missing) == 0, missing

    @staticmethod
    def validate_yaml_syntax(file_path: Path) -> Tuple[bool, Optional[str]]:
        """Validate YAML file syntax.

        Args:
            file_path: Path to YAML file

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            with open(file_path) as f:
                yaml.safe_load(f)
            return True, None
        except yaml.YAMLError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Failed to read file: {e}"

    @staticmethod
    def validate_service_file(file_path: Path) -> Tuple[bool, List[str]]:
        """Validate systemd service file.

        Args:
            file_path: Path to service file

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        if not file_path.exists():
            return False, [f"Service file not found: {file_path}"]

        content = file_path.read_text()

        # Check for required sections
        if "[Unit]" not in content:
            errors.append("Missing [Unit] section")
        if "[Service]" not in content:
            errors.append("Missing [Service] section")
        if "[Install]" not in content:
            errors.append("Missing [Install] section")

        # Check for basic service settings
        if "ExecStart=" not in content:
            errors.append("Missing ExecStart directive")

        return len(errors) == 0, errors
