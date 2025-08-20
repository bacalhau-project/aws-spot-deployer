#!/usr/bin/env python3
"""Deployment discovery module for detecting and validating deployment structures."""

from enum import Enum
from pathlib import Path
from typing import Optional, Tuple

from ..core.deployment import DeploymentConfig


class DeploymentMode(Enum):
    """Deployment mode enumeration."""

    PORTABLE = "portable"  # .spot/ directory with deployment.yaml
    CONVENTION = "convention"  # deployment/ directory with convention-based structure
    LEGACY = "legacy"  # Old instance/scripts structure


class DeploymentDiscovery:
    """Discovers and validates deployment structures."""

    def __init__(self, start_path: Optional[Path] = None):
        """Initialize deployment discovery.

        Args:
            start_path: Starting path for discovery (defaults to current directory)
        """
        self.start_path = Path(start_path) if start_path else Path.cwd()

    def detect_deployment_mode(self) -> DeploymentMode:
        """Detect the deployment mode based on directory structure.

        Returns:
            DeploymentMode indicating the type of deployment structure found
        """
        # Check for portable mode (.spot directory with deployment.yaml)
        spot_dir = self.start_path / ".spot"
        if spot_dir.exists() and (spot_dir / "deployment.yaml").exists():
            return DeploymentMode.PORTABLE

        # Check for convention mode (deployment/ directory)
        deployment_dir = self.start_path / "deployment"
        if deployment_dir.exists() and deployment_dir.is_dir():
            # Check if it has expected convention structure
            if (deployment_dir / "setup.sh").exists() or (deployment_dir / "init.sh").exists():
                return DeploymentMode.CONVENTION

        # Check for legacy mode (instance/scripts directory)
        instance_dir = self.start_path / "instance"
        if instance_dir.exists() and (instance_dir / "scripts").exists():
            return DeploymentMode.LEGACY

        # Default to legacy if nothing else found
        return DeploymentMode.LEGACY

    def find_project_root(self, max_depth: int = 5) -> Optional[Path]:
        """Find the project root by looking for deployment markers.

        Args:
            max_depth: Maximum directory levels to traverse up

        Returns:
            Path to project root or None if not found
        """
        current = self.start_path.resolve()

        for _ in range(max_depth):
            # Check for .spot directory
            if (current / ".spot").exists():
                return current

            # Check for deployment directory
            if (current / "deployment").exists():
                return current

            # Check for config.yaml (common root marker)
            if (current / "config.yaml").exists():
                return current

            # Check for instance directory (legacy)
            if (current / "instance").exists():
                return current

            # Move up one directory
            parent = current.parent
            if parent == current:  # Reached root
                break
            current = parent

        # If we're in a directory with any deployment markers, use it
        if (self.start_path / ".spot").exists() or (self.start_path / "deployment").exists():
            return self.start_path

        return None

    def validate_discovered_structure(self, mode: DeploymentMode, root: Path) -> Tuple[bool, list]:
        """Validate the discovered deployment structure.

        Args:
            mode: The deployment mode detected
            root: The project root path

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        if mode == DeploymentMode.PORTABLE:
            spot_dir = root / ".spot"

            # Check required files for portable mode
            required_files = [
                spot_dir / "deployment.yaml",
                spot_dir / "config.yaml",
            ]

            for file_path in required_files:
                if not file_path.exists():
                    errors.append(f"Missing required file: {file_path.relative_to(root)}")

            # Check optional but recommended directories
            recommended_dirs = [
                spot_dir / "scripts",
                spot_dir / "files",
                spot_dir / "services",
                spot_dir / "configs",
            ]

            for dir_path in recommended_dirs:
                if not dir_path.exists():
                    # Not an error, just note it doesn't exist
                    pass

        elif mode == DeploymentMode.CONVENTION:
            deployment_dir = root / "deployment"

            if not deployment_dir.exists():
                errors.append("Deployment directory not found")
            else:
                # Must have at least one setup script
                has_setup = (deployment_dir / "setup.sh").exists() or (
                    deployment_dir / "init.sh"
                ).exists()
                if not has_setup:
                    errors.append("No setup.sh or init.sh found in deployment directory")

        elif mode == DeploymentMode.LEGACY:
            # For legacy mode, just check instance directory exists
            instance_dir = root / "instance"
            if not instance_dir.exists():
                # Legacy mode is always "valid" as fallback
                pass

        return len(errors) == 0, errors

    def get_deployment_config(self) -> Optional[DeploymentConfig]:
        """Get deployment configuration based on discovered structure.

        Returns:
            DeploymentConfig object or None if discovery failed
        """
        # Find project root
        root = self.find_project_root()
        if not root:
            return None

        # Detect mode
        mode = self.detect_deployment_mode()

        # Validate structure
        is_valid, errors = self.validate_discovered_structure(mode, root)
        if not is_valid:
            # Log errors but continue
            for error in errors:
                print(f"Warning: {error}")

        # Create deployment config based on mode
        if mode == DeploymentMode.PORTABLE:
            spot_dir = root / ".spot"
            if spot_dir.exists():
                try:
                    return DeploymentConfig.from_spot_dir(spot_dir)
                except Exception as e:
                    print(f"Failed to load deployment config: {e}")
                    return None

        elif mode == DeploymentMode.CONVENTION:
            # For convention mode, build config from discovered files
            # This will be implemented in the convention scanner (Item 4)
            return None

        # For legacy mode, return None (will use legacy handling)
        return None
