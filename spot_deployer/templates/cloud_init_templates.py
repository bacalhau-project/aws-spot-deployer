#!/usr/bin/env python3
"""Cloud-init template system for customizable deployments."""

import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from ..core.deployment import DeploymentConfig

logger = logging.getLogger(__name__)


class CloudInitTemplate:
    """Manages cloud-init templates with variable substitution."""

    def __init__(self, template_path: Optional[Path] = None):
        """Initialize template with optional template file.

        Args:
            template_path: Path to template file (YAML format)
        """
        self.template_path = template_path
        self.template_content = None
        self.variables = {}

        if template_path and template_path.exists():
            self._load_template()

    def _load_template(self) -> None:
        """Load template from file."""
        if not self.template_path or not self.template_path.exists():
            raise FileNotFoundError(f"Template file not found: {self.template_path}")

        with open(self.template_path, "r") as f:
            self.template_content = f.read()

        logger.debug(f"Loaded template from {self.template_path}")

    def set_variables(self, variables: Dict[str, Any]) -> None:
        """Set variables for template substitution.

        Args:
            variables: Dictionary of variable names and values
        """
        self.variables = variables

    def add_variable(self, name: str, value: Any) -> None:
        """Add a single variable for substitution.

        Args:
            name: Variable name
            value: Variable value
        """
        self.variables[name] = value

    def render(self, deployment_config: Optional[DeploymentConfig] = None) -> str:
        """Render the template with variable substitution.

        Args:
            deployment_config: Optional deployment configuration for automatic variables

        Returns:
            Rendered cloud-init YAML string
        """
        if not self.template_content:
            if self.template_path:
                self._load_template()
            else:
                # Use default template if none provided
                self.template_content = self._get_default_template()

        # Build variables for substitution
        template_vars = self._build_template_variables(deployment_config)

        # Perform substitution
        rendered = self.template_content
        if rendered:
            for key, value in template_vars.items():
                # Support both {{VAR}} and ${VAR} syntax
                rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
                rendered = rendered.replace(f"${{{key}}}", str(value))

            # Validate the rendered YAML
            try:
                yaml.safe_load(rendered)
            except yaml.YAMLError as e:
                logger.warning(f"Rendered template is not valid YAML: {e}")
        else:
            rendered = ""

        return rendered

    def _build_template_variables(
        self, deployment_config: Optional[DeploymentConfig]
    ) -> Dict[str, str]:
        """Build template variables from deployment config and custom variables.

        Args:
            deployment_config: Optional deployment configuration

        Returns:
            Dictionary of template variables
        """
        vars = {}

        # Add deployment config variables if available
        if deployment_config:
            # Packages
            if deployment_config.packages:
                packages_yaml = "\n".join(f"  - {pkg}" for pkg in deployment_config.packages)
                vars["PACKAGES"] = packages_yaml
            else:
                vars["PACKAGES"] = ""

            # Scripts
            script_commands = []
            for script in deployment_config.scripts:
                cmd = script.get("command", "")
                if cmd:
                    script_commands.append(f"  - '{cmd}'")
            vars["SCRIPTS"] = "\n".join(script_commands) if script_commands else ""

            # Services
            service_names = []
            for service in deployment_config.services:
                if isinstance(service, dict):
                    path = service.get("path", "")
                    if path:
                        service_names.append(Path(path).name)
                else:
                    service_names.append(Path(service).name)
            vars["SERVICES"] = (
                "\n".join(f"  - {name}" for name in service_names) if service_names else ""
            )

            # Upload destinations
            upload_dirs = []
            for upload in deployment_config.uploads:
                dest = upload.get("destination", "")
                if dest:
                    upload_dirs.append(dest)
            vars["UPLOAD_DIRS"] = (
                "\n".join(f"  - {dir}" for dir in upload_dirs) if upload_dirs else ""
            )

        # Add custom variables (these override deployment config variables)
        vars.update(self.variables)

        return vars

    def _get_default_template(self) -> str:
        """Get the default cloud-init template.

        Returns:
            Default template string
        """
        return """#cloud-config

# Default cloud-init template for spot deployer
# Variables: {{PACKAGES}}, {{SCRIPTS}}, {{SERVICES}}, {{UPLOAD_DIRS}}

users:
  - default
  - name: ubuntu
    groups: sudo, docker
    shell: /bin/bash
    sudo: ALL=(ALL) NOPASSWD:ALL

packages:
{{PACKAGES}}

write_files:
  - path: /opt/deployment.marker
    permissions: '0644'
    content: |
      Deployment via template
      
  - path: /opt/deploy.sh
    permissions: '0755'
    content: |
      #!/bin/bash
      set -e
      
      echo "Starting deployment..."
      
      # Wait for uploads
      while [ ! -f /opt/uploads.complete ]; do
        sleep 2
      done
      
      # Run scripts
{{SCRIPTS}}
      
      # Start services
      systemctl daemon-reload
{{SERVICES}}
      
      echo "Deployment complete"
      touch /opt/deployment.complete

runcmd:
  - mkdir -p /opt/deployment
  - mkdir -p /opt/configs
  - mkdir -p /opt/secrets
{{UPLOAD_DIRS}}
  - nohup bash -c 'sleep 30; /opt/deploy.sh' > /opt/deploy.log 2>&1 &
"""

    def validate(self) -> tuple[bool, list[str]]:
        """Validate the template.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        if self.template_path and not self.template_path.exists():
            errors.append(f"Template file not found: {self.template_path}")

        if self.template_content:
            # Check for unsubstituted variables
            unsubstituted = re.findall(r"\{\{([^}]+)\}\}|\$\{([^}]+)\}", self.template_content)
            if unsubstituted:
                unique_vars = set(var[0] or var[1] for var in unsubstituted)
                # Check if these will be substituted
                for var in unique_vars:
                    if var not in self.variables and var not in [
                        "PACKAGES",
                        "SCRIPTS",
                        "SERVICES",
                        "UPLOAD_DIRS",
                    ]:
                        errors.append(f"Template variable not defined: {var}")

            # Try to parse as YAML
            try:
                yaml.safe_load(self.template_content)
            except yaml.YAMLError as e:
                errors.append(f"Template is not valid YAML: {e}")

        return len(errors) == 0, errors


class TemplateLibrary:
    """Library of pre-defined cloud-init templates."""

    # Template directory relative to this file
    TEMPLATE_DIR = Path(__file__).parent / "library"

    @classmethod
    def list_templates(cls) -> list[str]:
        """List available templates.

        Returns:
            List of template names
        """
        if not cls.TEMPLATE_DIR.exists():
            return []

        templates = []
        for file in cls.TEMPLATE_DIR.glob("*.yaml"):
            templates.append(file.stem)

        return sorted(templates)

    @classmethod
    def get_template(cls, name: str) -> CloudInitTemplate:
        """Get a template by name.

        Args:
            name: Template name (without .yaml extension)

        Returns:
            CloudInitTemplate instance

        Raises:
            FileNotFoundError: If template not found
        """
        template_path = cls.TEMPLATE_DIR / f"{name}.yaml"
        if not template_path.exists():
            available = cls.list_templates()
            raise FileNotFoundError(
                f"Template '{name}' not found. Available templates: {', '.join(available)}"
            )

        return CloudInitTemplate(template_path)

    @classmethod
    def get_template_path(cls, name: str) -> Path:
        """Get the path to a template file.

        Args:
            name: Template name

        Returns:
            Path to template file
        """
        return cls.TEMPLATE_DIR / f"{name}.yaml"


class TemplateInjector:
    """Injects custom content into cloud-init templates."""

    def __init__(self, base_template: str):
        """Initialize with base template.

        Args:
            base_template: Base cloud-init template string
        """
        self.base_template = base_template
        self.injections = {
            "packages": [],
            "write_files": [],
            "runcmd": [],
            "bootcmd": [],
        }

    def add_packages(self, packages: list[str]) -> None:
        """Add packages to install.

        Args:
            packages: List of package names
        """
        self.injections["packages"].extend(packages)

    def add_file(self, path: str, content: str, permissions: str = "0644") -> None:
        """Add a file to write.

        Args:
            path: File path
            content: File content
            permissions: File permissions
        """
        self.injections["write_files"].append(
            {"path": path, "content": content, "permissions": permissions}
        )

    def add_command(self, command: str, section: str = "runcmd") -> None:
        """Add a command to run.

        Args:
            command: Shell command
            section: Section to add to (runcmd or bootcmd)
        """
        if section not in ["runcmd", "bootcmd"]:
            raise ValueError(f"Invalid section: {section}")

        self.injections[section].append(command)

    def inject(self) -> str:
        """Inject content into the base template.

        Returns:
            Modified cloud-init template
        """
        # Parse the base template
        try:
            cloud_init = yaml.safe_load(self.base_template)
            # Check if it's a valid dict (cloud-init should be)
            if not isinstance(cloud_init, dict):
                logger.warning(
                    "Base template is not a valid cloud-init structure, returning without injections"
                )
                return self.base_template
        except yaml.YAMLError:
            # If not valid YAML, return as-is
            logger.warning("Base template is not valid YAML, returning without injections")
            return self.base_template

        # Inject packages
        if self.injections["packages"]:
            if "packages" not in cloud_init:
                cloud_init["packages"] = []
            cloud_init["packages"].extend(self.injections["packages"])

        # Inject write_files
        if self.injections["write_files"]:
            if "write_files" not in cloud_init:
                cloud_init["write_files"] = []
            for file_spec in self.injections["write_files"]:
                cloud_init["write_files"].append(
                    {
                        "path": file_spec["path"],
                        "permissions": file_spec["permissions"],
                        "content": file_spec["content"],
                    }
                )

        # Inject runcmd
        if self.injections["runcmd"]:
            if "runcmd" not in cloud_init:
                cloud_init["runcmd"] = []
            cloud_init["runcmd"].extend(self.injections["runcmd"])

        # Inject bootcmd
        if self.injections["bootcmd"]:
            if "bootcmd" not in cloud_init:
                cloud_init["bootcmd"] = []
            cloud_init["bootcmd"].extend(self.injections["bootcmd"])

        # Convert back to YAML
        return "#cloud-config\n" + yaml.dump(cloud_init, default_flow_style=False, sort_keys=False)
