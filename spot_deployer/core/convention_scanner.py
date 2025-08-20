#!/usr/bin/env python3
"""Convention scanner for auto-detecting deployment structure from deployment/ directory."""

import logging
from pathlib import Path
from typing import Optional

from .deployment import DeploymentConfig

logger = logging.getLogger(__name__)


class ConventionScanner:
    """Scans deployment/ directory and builds DeploymentConfig from conventions."""

    def __init__(self, deployment_dir: Path):
        """Initialize convention scanner.

        Args:
            deployment_dir: Path to deployment directory
        """
        self.deployment_dir = Path(deployment_dir)

    def scan(self) -> Optional[DeploymentConfig]:
        """Scan deployment directory and build configuration.

        Returns:
            DeploymentConfig built from discovered files, or None if invalid
        """
        if not self.deployment_dir.exists() or not self.deployment_dir.is_dir():
            logger.warning(f"Deployment directory not found: {self.deployment_dir}")
            return None

        # Initialize component lists
        packages = self._scan_packages()
        scripts = self._scan_scripts()
        uploads = self._scan_uploads()
        services = self._scan_services()

        # Log what was discovered
        self._log_discovery(packages, scripts, uploads, services)

        # Build and return config
        return DeploymentConfig(
            version=1, packages=packages, scripts=scripts, uploads=uploads, services=services
        )

    def _scan_packages(self) -> list:
        """Scan for package requirements.

        Returns:
            List of packages to install
        """
        packages = []

        # Check for requirements.txt (Python packages)
        requirements_file = self.deployment_dir / "requirements.txt"
        if requirements_file.exists():
            # Add Python and pip if requirements.txt exists
            packages.extend(["python3", "python3-pip"])
            logger.debug("Found requirements.txt, adding Python packages")

        # Check for package.json (Node.js packages)
        package_json = self.deployment_dir / "package.json"
        if package_json.exists():
            packages.append("nodejs")
            packages.append("npm")
            logger.debug("Found package.json, adding Node.js packages")

        # Check for Gemfile (Ruby packages)
        gemfile = self.deployment_dir / "Gemfile"
        if gemfile.exists():
            packages.append("ruby")
            packages.append("bundler")
            logger.debug("Found Gemfile, adding Ruby packages")

        # Check for go.mod (Go packages)
        go_mod = self.deployment_dir / "go.mod"
        if go_mod.exists():
            packages.append("golang")
            logger.debug("Found go.mod, adding Go package")

        # Check for Cargo.toml (Rust packages)
        cargo_toml = self.deployment_dir / "Cargo.toml"
        if cargo_toml.exists():
            packages.append("cargo")
            logger.debug("Found Cargo.toml, adding Rust packages")

        # Check for docker-compose.yml (Docker)
        docker_compose = self.deployment_dir / "docker-compose.yml"
        docker_compose_yaml = self.deployment_dir / "docker-compose.yaml"
        if docker_compose.exists() or docker_compose_yaml.exists():
            packages.append("docker.io")
            packages.append("docker-compose")
            logger.debug("Found docker-compose file, adding Docker packages")

        # Check for packages.txt (explicit package list)
        packages_txt = self.deployment_dir / "packages.txt"
        if packages_txt.exists():
            with open(packages_txt, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        packages.append(line)
            logger.debug(f"Found packages.txt with {len(packages)} packages")

        # Remove duplicates while preserving order
        seen = set()
        unique_packages = []
        for pkg in packages:
            if pkg not in seen:
                seen.add(pkg)
                unique_packages.append(pkg)

        return unique_packages

    def _scan_scripts(self) -> list:
        """Scan for setup scripts.

        Returns:
            List of script configurations
        """
        scripts = []

        # Check for main setup script (setup.sh or init.sh)
        setup_script = self.deployment_dir / "setup.sh"
        init_script = self.deployment_dir / "init.sh"

        if setup_script.exists():
            scripts.append(
                {"command": "/opt/deployment/setup.sh", "working_dir": "/opt/deployment"}
            )
            logger.debug("Found setup.sh as main script")
        elif init_script.exists():
            scripts.append({"command": "/opt/deployment/init.sh", "working_dir": "/opt/deployment"})
            logger.debug("Found init.sh as main script")

        # Scan scripts directory for additional scripts
        scripts_dir = self.deployment_dir / "scripts"
        if scripts_dir.exists() and scripts_dir.is_dir():
            # Sort scripts for deterministic execution order
            script_files = sorted(scripts_dir.glob("*.sh"))

            for script_file in script_files:
                # Skip backup files and hidden files
                if script_file.name.startswith(".") or script_file.name.endswith("~"):
                    continue

                scripts.append(
                    {
                        "command": f"/opt/deployment/scripts/{script_file.name}",
                        "working_dir": "/opt/deployment",
                    }
                )
                logger.debug(f"Found script: {script_file.name}")

        # Check for install script
        install_script = self.deployment_dir / "install.sh"
        if install_script.exists() and install_script not in [setup_script, init_script]:
            scripts.append(
                {"command": "/opt/deployment/install.sh", "working_dir": "/opt/deployment"}
            )
            logger.debug("Found install.sh")

        # Check for start script
        start_script = self.deployment_dir / "start.sh"
        if start_script.exists():
            scripts.append(
                {"command": "/opt/deployment/start.sh", "working_dir": "/opt/deployment"}
            )
            logger.debug("Found start.sh")

        return scripts

    def _scan_uploads(self) -> list:
        """Scan for files to upload.

        Returns:
            List of upload configurations
        """
        uploads = []

        # Always upload the entire deployment directory
        uploads.append(
            {
                "source": str(self.deployment_dir),
                "destination": "/opt/deployment",
                "permissions": "755",
            }
        )
        logger.debug("Adding deployment directory to uploads")

        # Check for configs directory
        configs_dir = self.deployment_dir / "configs"
        if configs_dir.exists() and configs_dir.is_dir():
            uploads.append(
                {"source": str(configs_dir), "destination": "/opt/configs", "permissions": "644"}
            )
            logger.debug("Found configs directory")

        # Check for files directory
        files_dir = self.deployment_dir / "files"
        if files_dir.exists() and files_dir.is_dir():
            uploads.append(
                {"source": str(files_dir), "destination": "/opt/files", "permissions": "644"}
            )
            logger.debug("Found files directory")

        # Check for secrets directory
        secrets_dir = self.deployment_dir / "secrets"
        if secrets_dir.exists() and secrets_dir.is_dir():
            uploads.append(
                {
                    "source": str(secrets_dir),
                    "destination": "/opt/secrets",
                    "permissions": "600",  # Restrictive permissions for secrets
                }
            )
            logger.debug("Found secrets directory (will use restrictive permissions)")

        # Check for .env file
        env_file = self.deployment_dir / ".env"
        if env_file.exists():
            uploads.append(
                {
                    "source": str(env_file),
                    "destination": "/opt/deployment/.env",
                    "permissions": "600",  # Restrictive permissions for env file
                }
            )
            logger.debug("Found .env file")

        return uploads

    def _scan_services(self) -> list:
        """Scan for systemd service files.

        Returns:
            List of service dictionaries with 'path' key
        """
        services = []
        seen_paths = set()

        # Check for services directory
        services_dir = self.deployment_dir / "services"
        if services_dir.exists() and services_dir.is_dir():
            # Find all .service files
            service_files = sorted(services_dir.glob("*.service"))

            for service_file in service_files:
                path_str = str(service_file)
                if path_str not in seen_paths:
                    services.append({"path": path_str})
                    seen_paths.add(path_str)
                    logger.debug(f"Found service: {service_file.name}")

        # Check for systemd directory (alternative location)
        systemd_dir = self.deployment_dir / "systemd"
        if systemd_dir.exists() and systemd_dir.is_dir():
            service_files = sorted(systemd_dir.glob("*.service"))

            for service_file in service_files:
                path_str = str(service_file)
                if path_str not in seen_paths:  # Avoid duplicates
                    services.append({"path": path_str})
                    seen_paths.add(path_str)
                    logger.debug(f"Found service in systemd/: {service_file.name}")

        # Check for individual service files in root of deployment
        root_services = sorted(self.deployment_dir.glob("*.service"))
        for service_file in root_services:
            path_str = str(service_file)
            if path_str not in seen_paths:
                services.append({"path": path_str})
                seen_paths.add(path_str)
                logger.debug(f"Found service in root: {service_file.name}")

        return services

    def _log_discovery(self, packages: list, scripts: list, uploads: list, services: list):
        """Log what was discovered during scanning.

        Args:
            packages: List of discovered packages
            scripts: List of discovered scripts
            uploads: List of discovered uploads
            services: List of discovered services
        """
        logger.info("Convention scanner discovery summary:")
        logger.info(f"  - Packages: {len(packages)} found")
        if packages:
            for pkg in packages[:5]:  # Show first 5
                logger.debug(f"    - {pkg}")
            if len(packages) > 5:
                logger.debug(f"    ... and {len(packages) - 5} more")

        logger.info(f"  - Scripts: {len(scripts)} found")
        for script in scripts:
            logger.debug(f"    - {script['command']}")

        logger.info(f"  - Uploads: {len(uploads)} directories/files")
        for upload in uploads:
            logger.debug(f"    - {upload['source']} -> {upload['destination']}")

        logger.info(f"  - Services: {len(services)} found")
        for service in services:
            if isinstance(service, dict):
                service_path = service.get("path", "")
            else:
                service_path = service
            logger.debug(f"    - {Path(service_path).name}")

    def validate(self) -> tuple[bool, list[str]]:
        """Validate that deployment directory has deployable content.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        if not self.deployment_dir.exists():
            errors.append(f"Deployment directory not found: {self.deployment_dir}")
            return False, errors

        if not self.deployment_dir.is_dir():
            errors.append(f"Deployment path is not a directory: {self.deployment_dir}")
            return False, errors

        # Check for at least one deployable item
        has_content = False

        # Check for setup scripts
        if (
            (self.deployment_dir / "setup.sh").exists()
            or (self.deployment_dir / "init.sh").exists()
            or (self.deployment_dir / "install.sh").exists()
            or (self.deployment_dir / "start.sh").exists()
        ):
            has_content = True

        # Check for scripts directory
        scripts_dir = self.deployment_dir / "scripts"
        if scripts_dir.exists() and any(scripts_dir.glob("*.sh")):
            has_content = True

        # Check for services
        services_dir = self.deployment_dir / "services"
        if services_dir.exists() and any(services_dir.glob("*.service")):
            has_content = True

        # Check for systemd directory
        systemd_dir = self.deployment_dir / "systemd"
        if systemd_dir.exists() and any(systemd_dir.glob("*.service")):
            has_content = True

        # Check for root service files
        if any(self.deployment_dir.glob("*.service")):
            has_content = True

        # Check for configs
        configs_dir = self.deployment_dir / "configs"
        if configs_dir.exists() and any(configs_dir.iterdir()):
            has_content = True

        # Check for docker-compose
        if (self.deployment_dir / "docker-compose.yml").exists() or (
            self.deployment_dir / "docker-compose.yaml"
        ).exists():
            has_content = True

        # Check for common package files
        if (
            (self.deployment_dir / "requirements.txt").exists()
            or (self.deployment_dir / "package.json").exists()
            or (self.deployment_dir / "Gemfile").exists()
            or (self.deployment_dir / "go.mod").exists()
            or (self.deployment_dir / "Cargo.toml").exists()
        ):
            has_content = True

        if not has_content:
            errors.append("Deployment directory has no deployable content")

        return len(errors) == 0, errors
