"""Portable cloud-init generator that creates cloud-init from DeploymentConfig."""

import logging
from pathlib import Path
from typing import Optional

from ..core.deployment import DeploymentConfig
from ..templates.cloud_init_templates import CloudInitTemplate
from ..utils.service_installer import ServiceInstaller

logger = logging.getLogger(__name__)


class PortableCloudInitGenerator:
    """Generates cloud-init configuration from DeploymentConfig."""

    def __init__(
        self, deployment_config: DeploymentConfig, ssh_public_key: Optional[str] = None
    ):
        """Initialize generator with deployment configuration.

        Args:
            deployment_config: DeploymentConfig object with deployment specs
            ssh_public_key: Optional SSH public key to add to the ubuntu user
        """
        self.config = deployment_config
        self.ssh_public_key = ssh_public_key

    def generate(self) -> str:
        """Generate complete cloud-init YAML configuration.

        Returns:
            String containing the cloud-init YAML
        """
        sections = []

        # Start with cloud-init header
        sections.append("#cloud-config")

        # Add package installation
        if self.config.packages:
            sections.append(self._generate_packages_section())

        # Add users section (for creating directories)
        sections.append(self._generate_users_section())

        # Add write_files section for inline files
        write_files = self._generate_write_files_section()
        if write_files:
            sections.append(write_files)

        # Add runcmd section for scripts and setup
        runcmd = self._generate_runcmd_section()
        if runcmd:
            sections.append(runcmd)

        # Join all sections with newlines
        cloud_init = "\n\n".join(filter(None, sections))

        logger.debug(f"Generated cloud-init with {len(sections)} sections")
        return cloud_init

    def _generate_packages_section(self) -> str:
        """Generate packages section for cloud-init.

        Returns:
            YAML string for packages section
        """
        if not self.config.packages:
            return ""

        packages_yaml = "packages:\n"
        for package in self.config.packages:
            packages_yaml += f"  - {package}\n"

        logger.debug(
            f"Generated packages section with {len(self.config.packages)} packages"
        )
        return packages_yaml.rstrip()

    def _generate_users_section(self) -> str:
        """Generate users section to ensure ubuntu user exists.

        Returns:
            YAML string for users section
        """
        users_yaml = """users:
  - default
  - name: ubuntu
    groups: sudo, docker
    shell: /bin/bash
    sudo: ALL=(ALL) NOPASSWD:ALL"""

        # Add SSH key if provided
        if self.ssh_public_key:
            users_yaml += f"""
    ssh_authorized_keys:
      - {self.ssh_public_key}"""

        return users_yaml

    def _generate_write_files_section(self) -> str:
        """Generate write_files section for inline configuration files.

        Returns:
            YAML string for write_files section
        """
        write_files = []

        # Add a minimal deployment script that waits for uploads
        deployment_script = """#!/bin/bash
set -e

echo "Waiting for file uploads to complete..."
# Wait for upload marker file that SSH uploader creates
while [ ! -f /opt/uploads.complete ]; do
    sleep 2
done

echo "Starting deployment..."

# Make uploaded scripts executable
find /opt/deployment -name "*.sh" -type f -exec chmod +x {} \\; 2>/dev/null || true

# Execute main setup script if it exists
if [ -f /opt/deployment/setup.sh ]; then
    cd /opt/deployment
    ./setup.sh
elif [ -f /opt/deployment/init.sh ]; then
    cd /opt/deployment
    ./init.sh
fi

# Extract tarball if it exists
if [ -f /opt/deployment.tar.gz ]; then
    echo "Extracting deployment tarball..."
    cd /opt
    tar -xzf deployment.tar.gz
    rm -f deployment.tar.gz
fi

echo "Deployment completed"
touch /opt/deployment.complete
"""

        write_files.append(
            {
                "path": "/opt/deploy.sh",
                "content": deployment_script,
                "permissions": "0755",
            }
        )

        # Only add small marker files, not service files (those get uploaded)
        write_files.append(
            {
                "path": "/opt/deployment.marker",
                "content": "Portable deployment\n",
                "permissions": "0644",
            }
        )

        if not write_files:
            return ""

        # Build YAML
        yaml_lines = ["write_files:"]
        for file_spec in write_files:
            yaml_lines.append(f"  - path: {file_spec['path']}")
            yaml_lines.append(f"    permissions: '{file_spec['permissions']}'")
            yaml_lines.append("    content: |")
            # Indent content properly
            for line in file_spec["content"].splitlines():
                yaml_lines.append(f"      {line}")

        return "\n".join(yaml_lines)

    def _generate_runcmd_section(self) -> str:
        """Generate runcmd section for script execution and tarball handling.

        Returns:
            YAML string for runcmd section
        """
        commands = []

        # Create necessary directories
        commands.extend(
            [
                "mkdir -p /opt/deployment",
            ]
        )

        # Add script to wait for upload completion marker
        wait_script = """
# Wait for upload completion marker with timeout
echo "Waiting for file upload to complete..."
MAX_WAIT=180  # 3 minutes timeout (reduced from 5)
WAIT_COUNT=0
while [ ! -f /tmp/UPLOAD_COMPLETE ] && [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    sleep 5
    WAIT_COUNT=$((WAIT_COUNT + 5))
    if [ $((WAIT_COUNT % 30)) -eq 0 ]; then
        echo "Still waiting for upload to complete... ($WAIT_COUNT seconds)"
    fi
done

# If timeout, create marker anyway to prevent hanging
if [ ! -f /tmp/UPLOAD_COMPLETE ]; then
    echo "WARNING: Upload timeout - proceeding anyway"
    touch /tmp/UPLOAD_COMPLETE
fi

if [ ! -f /tmp/UPLOAD_COMPLETE ]; then
    echo "WARNING: Upload did not complete within timeout period"
    echo "Continuing anyway to prevent instance from being stuck"
    echo "Files may not be properly deployed"
fi

echo "Upload complete marker detected"
"""
        commands.append(wait_script)

        # Handle tarball deployment if specified
        if hasattr(self.config, "tarball_source") and self.config.tarball_source:
            # Add extraction commands for the tarball that will be uploaded
            extract_script = """
# Extract deployment tarball (after upload is complete)
if [ -f /tmp/deployment.tar.gz ]; then
    echo "Extracting deployment package..."
    mkdir -p /opt/deployment
    tar -xzf /tmp/deployment.tar.gz -C /opt/deployment
    rm -f /tmp/deployment.tar.gz
    chown -R ubuntu:ubuntu /opt/deployment

    # Make any scripts executable
    find /opt/deployment -name "*.sh" -type f -exec chmod +x {} \\;

    echo "Deployment package extracted successfully"
    echo "Directory structure:"
    ls -la /opt/deployment/
else
    echo "Warning: No deployment tarball found at /tmp/deployment.tar.gz"
fi
"""
            commands.append(extract_script)

            # Add command to run setup script if it exists in the extracted tarball
            setup_script = """
# Run setup script from extracted tarball if it exists
if [ -f /opt/deployment/setup.sh ]; then
    echo "Running setup.sh script..."
    chmod +x /opt/deployment/setup.sh
    cd /opt/deployment
    ./setup.sh
    echo "Setup script completed"
else
    echo "No setup.sh found in deployment package"
fi

# Mark deployment as complete
touch /opt/deployment.complete
echo "Deployment process finished"
"""
            commands.append(setup_script)

        # Install services if defined
        if self.config.services:
            installer = ServiceInstaller(self.config)
            service_commands = installer.generate_install_commands()

            if service_commands:
                # Create service installation script
                service_script = """cat > /tmp/install_services.sh << 'EOF'
#!/bin/bash
set -e
# Wait for files to be uploaded
while [ ! -f /opt/uploads.complete ] && [ ! -f /opt/deployment.complete ]; do
    sleep 2
done
"""
                for cmd in service_commands:
                    if not cmd.startswith("#"):
                        service_script += f"{cmd}\n"
                service_script += """EOF
chmod +x /tmp/install_services.sh
nohup bash -c 'sleep 45; /tmp/install_services.sh' > /opt/services.log 2>&1 &"""

                commands.append(service_script)

        # Run the deployment script in background after delay
        # This allows SSH to connect and upload files first
        commands.append(
            "nohup bash -c 'sleep 30; /opt/deploy.sh' > /opt/deploy.log 2>&1 &"
        )

        if not commands:
            return ""

        # Build YAML
        yaml_lines = ["runcmd:"]
        for cmd in commands:
            # For multi-line commands, use the literal style
            if "\n" in cmd:
                yaml_lines.append("  - |")
                for line in cmd.split("\n"):
                    yaml_lines.append(f"    {line}")
            else:
                # Escape special characters in YAML
                escaped_cmd = cmd.replace("'", "''")
                yaml_lines.append(f"  - '{escaped_cmd}'")

        return "\n".join(yaml_lines)

    def generate_with_template(
        self, template_path: Optional[Path] = None, template_name: Optional[str] = None
    ) -> str:
        """Generate cloud-init using a template file or library template.

        Args:
            template_path: Path to cloud-init template file
            template_name: Name of library template to use

        Returns:
            String containing the cloud-init YAML
        """
        if template_path and template_path.exists():
            # Use provided template file
            template = CloudInitTemplate(template_path)
            logger.info(f"Using custom template: {template_path}")
            # Add SSH key as a template variable if available
            if self.ssh_public_key:
                template.add_variable("SSH_PUBLIC_KEY", self.ssh_public_key)
            return template.render(self.config)
        elif template_name:
            # Use library template
            from amauo.templates.cloud_init_templates import TemplateLibrary

            try:
                template = TemplateLibrary.get_template(template_name)
                logger.info(f"Using library template: {template_name}")
                # Add SSH key as a template variable if available
                if self.ssh_public_key:
                    template.add_variable("SSH_PUBLIC_KEY", self.ssh_public_key)
                return template.render(self.config)
            except FileNotFoundError as e:
                logger.warning(f"Template not found: {e}")

        # Fall back to regular generation
        return self.generate()

    def _generate_packages_list(self) -> str:
        """Generate formatted list of packages for template.

        Returns:
            Formatted package list string
        """
        if not self.config.packages:
            return ""

        return "\n".join(f"  - {pkg}" for pkg in self.config.packages)

    def _generate_scripts_list(self) -> str:
        """Generate formatted list of scripts for template.

        Returns:
            Formatted scripts list string
        """
        if not self.config.scripts:
            return ""

        script_cmds = []
        for script in self.config.scripts:
            cmd = script.get("command", "")
            if cmd:
                script_cmds.append(f"  - '{cmd}'")

        return "\n".join(script_cmds)

    def _generate_services_list(self) -> str:
        """Generate formatted list of services for template.

        Returns:
            Formatted services list string
        """
        if not self.config.services:
            return ""

        service_names = []
        for s in self.config.services:
            if isinstance(s, dict):
                path = s.get("path")
                if path:
                    service_names.append(Path(path).name)
            else:
                service_names.append(Path(s).name)  # type: ignore[unreachable]
        return "\n".join(f"  - {name}" for name in service_names)

    def validate(self) -> tuple[bool, list[str]]:
        """Validate the deployment configuration for cloud-init generation.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check for excessively large package lists
        if len(self.config.packages) > 100:
            errors.append(
                f"Too many packages ({len(self.config.packages)}), may exceed cloud-init limits"
            )

        # Check for script paths
        for script in self.config.scripts:
            command = script.get("command", "")
            if command and not command.startswith("/"):
                errors.append(f"Script command should use absolute path: {command}")

        # Check service files exist
        for service_item in self.config.services:
            if isinstance(service_item, dict):
                service_path = service_item.get("path")
                if not service_path:
                    continue
            else:
                service_path = service_item  # type: ignore[unreachable]
            service_file = Path(service_path)
            if not service_file.exists():
                errors.append(f"Service file not found: {service_path}")

        # Check upload destinations
        for upload in self.config.uploads:
            dest = upload.get("destination", "")
            if not dest.startswith("/"):
                errors.append(f"Upload destination should use absolute path: {dest}")

        return len(errors) == 0, errors


class CloudInitBuilder:
    """Builder pattern for constructing cloud-init configurations."""

    def __init__(self) -> None:
        """Initialize an empty cloud-init builder."""
        self.packages: list[str] = []
        self.files: list[dict] = []
        self.commands: list[str] = []
        self.users: list[dict] = []

    def add_package(self, package: str) -> "CloudInitBuilder":
        """Add a package to install.

        Args:
            package: Package name

        Returns:
            Self for chaining
        """
        self.packages.append(package)
        return self

    def add_packages(self, packages: list[str]) -> "CloudInitBuilder":
        """Add multiple packages to install.

        Args:
            packages: List of package names

        Returns:
            Self for chaining
        """
        self.packages.extend(packages)
        return self

    def add_file(
        self, path: str, content: str, permissions: str = "0644"
    ) -> "CloudInitBuilder":
        """Add a file to write.

        Args:
            path: File path
            content: File content
            permissions: File permissions

        Returns:
            Self for chaining
        """
        self.files.append(
            {"path": path, "content": content, "permissions": permissions}
        )
        return self

    def add_command(self, command: str) -> "CloudInitBuilder":
        """Add a command to run.

        Args:
            command: Shell command

        Returns:
            Self for chaining
        """
        self.commands.append(command)
        return self

    def add_commands(self, commands: list[str]) -> "CloudInitBuilder":
        """Add multiple commands to run.

        Args:
            commands: List of shell commands

        Returns:
            Self for chaining
        """
        self.commands.extend(commands)
        return self

    def build(self) -> str:
        """Build the final cloud-init YAML.

        Returns:
            Complete cloud-init YAML string
        """
        sections = ["#cloud-config"]

        # Add packages
        if self.packages:
            sections.append("packages:")
            for pkg in self.packages:
                sections.append(f"  - {pkg}")

        # Add files
        if self.files:
            sections.append("\nwrite_files:")
            for file_spec in self.files:
                sections.append(f"  - path: {file_spec['path']}")
                sections.append(f"    permissions: '{file_spec['permissions']}'")
                sections.append("    content: |")
                for line in file_spec["content"].splitlines():
                    sections.append(f"      {line}")

        # Add commands
        if self.commands:
            sections.append("\nruncmd:")
            for cmd in self.commands:
                escaped = cmd.replace("'", "''")
                sections.append(f"  - '{escaped}'")

        return "\n".join(sections)
