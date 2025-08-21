"""Service installer for systemd services."""

import logging
from pathlib import Path
from typing import Dict, List

from ..core.deployment import DeploymentConfig

logger = logging.getLogger(__name__)


class ServiceInstaller:
    """Handles installation and management of systemd services."""

    def __init__(self, deployment_config: DeploymentConfig):
        """Initialize service installer.

        Args:
            deployment_config: DeploymentConfig with service definitions
        """
        self.config = deployment_config
        self.service_dir = "/etc/systemd/system"

    def generate_install_commands(self) -> List[str]:
        """Generate commands to install and start services.

        Returns:
            List of shell commands to install services
        """
        if not self.config.services:
            logger.info("No services defined in deployment configuration")
            return []

        commands = []

        for service in self.config.services:
            service_file = service.get("file")
            service_name = service.get("name")
            enabled = service.get("enabled", True)
            start = service.get("start", True)

            if not service_file or not service_name:
                logger.warning(f"Service missing required fields: {service}")
                continue

            # Generate commands for this service
            service_commands = self._generate_service_commands(
                service_file, service_name, enabled, start
            )
            commands.extend(service_commands)

        return commands

    def _generate_service_commands(
        self, service_file: str, service_name: str, enabled: bool, start: bool
    ) -> List[str]:
        """Generate commands for a single service.

        Args:
            service_file: Path to service file (relative to deployment)
            service_name: Name of the service
            enabled: Whether to enable the service
            start: Whether to start the service

        Returns:
            List of commands for this service
        """
        commands = []

        # Copy service file to systemd directory
        source_path = f"/opt/deployment/{service_file}"
        dest_path = f"{self.service_dir}/{service_name}.service"

        commands.append(f"# Install {service_name} service")
        commands.append(f"cp {source_path} {dest_path}")
        commands.append(f"chmod 644 {dest_path}")

        # Reload systemd daemon
        commands.append("systemctl daemon-reload")

        # Enable service if requested
        if enabled:
            commands.append(f"systemctl enable {service_name}")

        # Start service if requested
        if start:
            commands.append(f"systemctl start {service_name}")

        # Add status check
        commands.append(f"systemctl status {service_name} --no-pager || true")

        return commands

    def generate_cloud_init_snippet(self) -> str:
        """Generate cloud-init snippet for service installation.

        Returns:
            YAML string for runcmd section
        """
        commands = self.generate_install_commands()

        if not commands:
            return ""

        # Build YAML snippet
        yaml_lines = []
        for cmd in commands:
            # Skip comments in YAML
            if cmd.startswith("#"):
                continue
            # Escape special characters
            escaped_cmd = cmd.replace("'", "''")
            yaml_lines.append(f"  - '{escaped_cmd}'")

        return "\n".join(yaml_lines)

    def generate_service_script(self) -> str:
        """Generate a standalone script to install services.

        Returns:
            Shell script content
        """
        commands = self.generate_install_commands()

        if not commands:
            return ""

        script = """#!/bin/bash
# Service installation script
set -e

echo "Installing systemd services..."

"""

        for cmd in commands:
            script += f"{cmd}\n"

        script += """
echo "Service installation complete!"
"""

        return script

    def validate_services(self) -> tuple[bool, List[str]]:
        """Validate service definitions.

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        if not self.config.services:
            return True, []

        for i, service in enumerate(self.config.services):
            service_errors = []

            # Check required fields
            if not service.get("file"):
                service_errors.append(f"Service {i + 1}: Missing 'file' field")

            if not service.get("name"):
                service_errors.append(f"Service {i + 1}: Missing 'name' field")

            # Check if service file exists
            if service.get("file"):
                service_path = self.config.spot_dir / service["file"]
                if not service_path.exists():
                    service_errors.append(f"Service {i + 1}: File not found: {service_path}")
                else:
                    # Validate it's a valid systemd service file
                    is_valid, validation_errors = self._validate_service_file(service_path)
                    if not is_valid:
                        service_errors.extend(
                            [f"Service {i + 1}: {err}" for err in validation_errors]
                        )

            errors.extend(service_errors)

        return len(errors) == 0, errors

    def _validate_service_file(self, service_path: Path) -> tuple[bool, List[str]]:
        """Validate a systemd service file.

        Args:
            service_path: Path to service file

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        try:
            content = service_path.read_text()

            # Check for required sections
            if "[Unit]" not in content:
                errors.append("Missing [Unit] section")
            if "[Service]" not in content:
                errors.append("Missing [Service] section")
            if "[Install]" not in content:
                errors.append("Missing [Install] section")

            # Check for basic directives
            if "ExecStart=" not in content:
                errors.append("Missing ExecStart directive")

            # Check for Description
            if "Description=" not in content:
                errors.append("Missing Description")

        except Exception as e:
            errors.append(f"Failed to read service file: {e}")

        return len(errors) == 0, errors

    def get_service_dependencies(self) -> Dict[str, List[str]]:
        """Extract service dependencies from service files.

        Returns:
            Dictionary mapping service names to their dependencies
        """
        dependencies = {}

        for service in self.config.services:
            service_name = service.get("name")
            service_file = service.get("file")

            if not service_name or not service_file:
                continue

            service_path = self.config.spot_dir / service_file
            if not service_path.exists():
                continue

            deps = self._extract_dependencies(service_path)
            if deps:
                dependencies[service_name] = deps

        return dependencies

    def _extract_dependencies(self, service_path: Path) -> List[str]:
        """Extract dependencies from a service file.

        Args:
            service_path: Path to service file

        Returns:
            List of dependency service names
        """
        deps = []

        try:
            content = service_path.read_text()

            # Look for After= directive
            for line in content.split("\n"):
                if line.startswith("After="):
                    after_deps = line.replace("After=", "").split()
                    deps.extend(after_deps)

                # Also check Requires= and Wants=
                if line.startswith("Requires="):
                    required = line.replace("Requires=", "").split()
                    deps.extend(required)

                if line.startswith("Wants="):
                    wanted = line.replace("Wants=", "").split()
                    deps.extend(wanted)

        except Exception as e:
            logger.warning(f"Failed to extract dependencies from {service_path}: {e}")

        # Filter out system services
        system_services = [
            "network.target",
            "multi-user.target",
            "graphical.target",
            "basic.target",
            "sysinit.target",
        ]
        deps = [d for d in deps if d not in system_services]

        return deps

    def generate_health_checks(self) -> List[str]:
        """Generate health check commands for services.

        Returns:
            List of health check commands
        """
        commands = []

        for service in self.config.services:
            service_name = service.get("name")
            if service_name:
                commands.append(
                    f"systemctl is-active {service_name} || echo '{service_name} is not running'"
                )

        return commands
