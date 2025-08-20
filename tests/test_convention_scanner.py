#!/usr/bin/env python3
"""Tests for the convention scanner module."""

import tempfile
import unittest
from pathlib import Path

from spot_deployer.core.convention_scanner import ConventionScanner
from spot_deployer.core.deployment import DeploymentConfig


class TestConventionScanner(unittest.TestCase):
    """Test convention scanner functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_path = Path(self.temp_dir.name)
        self.deployment_dir = self.test_path / "deployment"
        self.deployment_dir.mkdir()

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_scan_empty_directory(self):
        """Test scanning an empty deployment directory."""
        scanner = ConventionScanner(self.deployment_dir)
        config = scanner.scan()

        self.assertIsNotNone(config)
        self.assertIsInstance(config, DeploymentConfig)
        self.assertEqual(config.version, 1)
        self.assertEqual(len(config.packages), 0)
        self.assertEqual(len(config.scripts), 0)
        # Should always have deployment dir upload
        self.assertEqual(len(config.uploads), 1)
        self.assertEqual(len(config.services), 0)

    def test_scan_setup_script(self):
        """Test scanning with setup.sh script."""
        setup_script = self.deployment_dir / "setup.sh"
        setup_script.write_text("#!/bin/bash\necho 'setup'\n")

        scanner = ConventionScanner(self.deployment_dir)
        config = scanner.scan()

        self.assertIsNotNone(config)
        self.assertEqual(len(config.scripts), 1)
        self.assertEqual(config.scripts[0]["command"], "/opt/deployment/setup.sh")
        self.assertEqual(config.scripts[0]["working_dir"], "/opt/deployment")

    def test_scan_init_script(self):
        """Test scanning with init.sh script."""
        init_script = self.deployment_dir / "init.sh"
        init_script.write_text("#!/bin/bash\necho 'init'\n")

        scanner = ConventionScanner(self.deployment_dir)
        config = scanner.scan()

        self.assertIsNotNone(config)
        self.assertEqual(len(config.scripts), 1)
        self.assertEqual(config.scripts[0]["command"], "/opt/deployment/init.sh")

    def test_scan_scripts_directory(self):
        """Test scanning scripts directory."""
        scripts_dir = self.deployment_dir / "scripts"
        scripts_dir.mkdir()

        # Create multiple scripts
        (scripts_dir / "01-install.sh").write_text("#!/bin/bash\n")
        (scripts_dir / "02-configure.sh").write_text("#!/bin/bash\n")
        (scripts_dir / "03-start.sh").write_text("#!/bin/bash\n")

        scanner = ConventionScanner(self.deployment_dir)
        config = scanner.scan()

        self.assertEqual(len(config.scripts), 3)
        # Should be in sorted order
        self.assertEqual(config.scripts[0]["command"], "/opt/deployment/scripts/01-install.sh")
        self.assertEqual(config.scripts[1]["command"], "/opt/deployment/scripts/02-configure.sh")
        self.assertEqual(config.scripts[2]["command"], "/opt/deployment/scripts/03-start.sh")

    def test_scan_packages_python(self):
        """Test scanning Python package requirements."""
        requirements = self.deployment_dir / "requirements.txt"
        requirements.write_text("flask==2.0.1\nrequests\n")

        scanner = ConventionScanner(self.deployment_dir)
        config = scanner.scan()

        self.assertIn("python3", config.packages)
        self.assertIn("python3-pip", config.packages)

    def test_scan_packages_nodejs(self):
        """Test scanning Node.js packages."""
        package_json = self.deployment_dir / "package.json"
        package_json.write_text('{"name": "test", "version": "1.0.0"}')

        scanner = ConventionScanner(self.deployment_dir)
        config = scanner.scan()

        self.assertIn("nodejs", config.packages)
        self.assertIn("npm", config.packages)

    def test_scan_packages_docker(self):
        """Test scanning Docker compose files."""
        docker_compose = self.deployment_dir / "docker-compose.yml"
        docker_compose.write_text("version: '3'\nservices:\n  app:\n    image: nginx\n")

        scanner = ConventionScanner(self.deployment_dir)
        config = scanner.scan()

        self.assertIn("docker.io", config.packages)
        self.assertIn("docker-compose", config.packages)

    def test_scan_packages_explicit(self):
        """Test scanning explicit packages.txt file."""
        packages_txt = self.deployment_dir / "packages.txt"
        packages_txt.write_text("nginx\n# Comment\npostgresql\n\nredis\n")

        scanner = ConventionScanner(self.deployment_dir)
        config = scanner.scan()

        self.assertIn("nginx", config.packages)
        self.assertIn("postgresql", config.packages)
        self.assertIn("redis", config.packages)
        # Comments and empty lines should be ignored
        self.assertNotIn("# Comment", config.packages)
        self.assertNotIn("", config.packages)

    def test_scan_services_directory(self):
        """Test scanning services directory."""
        services_dir = self.deployment_dir / "services"
        services_dir.mkdir()

        # Create service files
        (services_dir / "app.service").write_text(
            "[Unit]\nDescription=App\n[Service]\nExecStart=/usr/bin/app\n"
        )
        (services_dir / "worker.service").write_text(
            "[Unit]\nDescription=Worker\n[Service]\nExecStart=/usr/bin/worker\n"
        )

        scanner = ConventionScanner(self.deployment_dir)
        config = scanner.scan()

        self.assertEqual(len(config.services), 2)
        service_paths = [s.get("path") for s in config.services if isinstance(s, dict)]
        service_names = [Path(p).name for p in service_paths if p]
        self.assertIn("app.service", service_names)
        self.assertIn("worker.service", service_names)

    def test_scan_systemd_directory(self):
        """Test scanning systemd directory (alternative location)."""
        systemd_dir = self.deployment_dir / "systemd"
        systemd_dir.mkdir()

        (systemd_dir / "daemon.service").write_text("[Unit]\nDescription=Daemon\n")

        scanner = ConventionScanner(self.deployment_dir)
        config = scanner.scan()

        self.assertEqual(len(config.services), 1)
        service_path = (
            config.services[0].get("path")
            if isinstance(config.services[0], dict)
            else config.services[0]
        )
        self.assertIn("daemon.service", Path(service_path).name)

    def test_scan_root_service_files(self):
        """Test scanning service files in deployment root."""
        (self.deployment_dir / "main.service").write_text("[Unit]\nDescription=Main\n")

        scanner = ConventionScanner(self.deployment_dir)
        config = scanner.scan()

        self.assertEqual(len(config.services), 1)
        service_path = (
            config.services[0].get("path")
            if isinstance(config.services[0], dict)
            else config.services[0]
        )
        self.assertIn("main.service", Path(service_path).name)

    def test_scan_configs_directory(self):
        """Test scanning configs directory."""
        configs_dir = self.deployment_dir / "configs"
        configs_dir.mkdir()
        (configs_dir / "app.conf").write_text("config data")

        scanner = ConventionScanner(self.deployment_dir)
        config = scanner.scan()

        # Should have deployment dir + configs dir
        self.assertEqual(len(config.uploads), 2)
        upload_dests = [u["destination"] for u in config.uploads]
        self.assertIn("/opt/configs", upload_dests)

    def test_scan_files_directory(self):
        """Test scanning files directory."""
        files_dir = self.deployment_dir / "files"
        files_dir.mkdir()
        (files_dir / "data.txt").write_text("data")

        scanner = ConventionScanner(self.deployment_dir)
        config = scanner.scan()

        upload_dests = [u["destination"] for u in config.uploads]
        self.assertIn("/opt/files", upload_dests)

    def test_scan_secrets_directory(self):
        """Test scanning secrets directory with restrictive permissions."""
        secrets_dir = self.deployment_dir / "secrets"
        secrets_dir.mkdir()
        (secrets_dir / "api_key.txt").write_text("secret")

        scanner = ConventionScanner(self.deployment_dir)
        config = scanner.scan()

        # Find the secrets upload
        secrets_upload = None
        for upload in config.uploads:
            if upload["destination"] == "/opt/secrets":
                secrets_upload = upload
                break

        self.assertIsNotNone(secrets_upload)
        if secrets_upload:
            self.assertEqual(secrets_upload["permissions"], "600")  # Restrictive

    def test_scan_env_file(self):
        """Test scanning .env file."""
        env_file = self.deployment_dir / ".env"
        env_file.write_text("DATABASE_URL=postgres://localhost/db\n")

        scanner = ConventionScanner(self.deployment_dir)
        config = scanner.scan()

        # Find the env file upload
        env_upload = None
        for upload in config.uploads:
            if upload["destination"] == "/opt/deployment/.env":
                env_upload = upload
                break

        self.assertIsNotNone(env_upload)
        if env_upload:
            self.assertEqual(env_upload["permissions"], "600")  # Restrictive

    def test_scan_multiple_script_types(self):
        """Test scanning when multiple script types exist."""
        # Create various scripts
        (self.deployment_dir / "setup.sh").write_text("#!/bin/bash\n")
        (self.deployment_dir / "install.sh").write_text("#!/bin/bash\n")
        (self.deployment_dir / "start.sh").write_text("#!/bin/bash\n")

        scanner = ConventionScanner(self.deployment_dir)
        config = scanner.scan()

        # All scripts should be included
        self.assertEqual(len(config.scripts), 3)
        script_commands = [s["command"] for s in config.scripts]
        self.assertIn("/opt/deployment/setup.sh", script_commands)
        self.assertIn("/opt/deployment/install.sh", script_commands)
        self.assertIn("/opt/deployment/start.sh", script_commands)

    def test_scan_no_duplicate_packages(self):
        """Test that duplicate packages are removed."""
        # Create multiple files that would add the same packages
        packages_txt = self.deployment_dir / "packages.txt"
        packages_txt.write_text("python3\nnginx\npython3\n")

        requirements = self.deployment_dir / "requirements.txt"
        requirements.write_text("flask\n")  # This also adds python3

        scanner = ConventionScanner(self.deployment_dir)
        config = scanner.scan()

        # python3 should only appear once
        python_count = config.packages.count("python3")
        self.assertEqual(python_count, 1)
        nginx_count = config.packages.count("nginx")
        self.assertEqual(nginx_count, 1)

    def test_validate_valid_directory(self):
        """Test validation of valid deployment directory."""
        (self.deployment_dir / "setup.sh").write_text("#!/bin/bash\n")

        scanner = ConventionScanner(self.deployment_dir)
        is_valid, errors = scanner.validate()

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_empty_directory(self):
        """Test validation of empty deployment directory."""
        scanner = ConventionScanner(self.deployment_dir)
        is_valid, errors = scanner.validate()

        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
        self.assertIn("no deployable content", errors[0])

    def test_validate_missing_directory(self):
        """Test validation when deployment directory doesn't exist."""
        missing_dir = self.test_path / "nonexistent"
        scanner = ConventionScanner(missing_dir)
        is_valid, errors = scanner.validate()

        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
        self.assertIn("not found", errors[0])

    def test_validate_not_directory(self):
        """Test validation when path is not a directory."""
        not_dir = self.test_path / "file.txt"
        not_dir.write_text("not a directory")

        scanner = ConventionScanner(not_dir)
        is_valid, errors = scanner.validate()

        self.assertFalse(is_valid)
        self.assertIn("not a directory", errors[0])

    def test_scan_comprehensive_project(self):
        """Test scanning a comprehensive project with all conventions."""
        # Create a full project structure
        (self.deployment_dir / "setup.sh").write_text("#!/bin/bash\n")

        scripts_dir = self.deployment_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "install.sh").write_text("#!/bin/bash\n")

        services_dir = self.deployment_dir / "services"
        services_dir.mkdir()
        (services_dir / "app.service").write_text("[Unit]\n")

        configs_dir = self.deployment_dir / "configs"
        configs_dir.mkdir()
        (configs_dir / "nginx.conf").write_text("server {}\n")

        (self.deployment_dir / "requirements.txt").write_text("flask\n")
        (self.deployment_dir / "docker-compose.yml").write_text("version: '3'\n")
        (self.deployment_dir / ".env").write_text("SECRET=value\n")

        scanner = ConventionScanner(self.deployment_dir)
        config = scanner.scan()

        # Should have detected everything
        self.assertGreater(len(config.packages), 0)
        self.assertGreater(len(config.scripts), 0)
        self.assertGreater(len(config.uploads), 1)  # At least deployment dir
        self.assertGreater(len(config.services), 0)

        # Validate it's all valid
        is_valid, errors = scanner.validate()
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)


if __name__ == "__main__":
    unittest.main()
