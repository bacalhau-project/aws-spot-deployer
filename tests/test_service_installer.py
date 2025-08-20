#!/usr/bin/env python3
"""Tests for ServiceInstaller class."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from spot_deployer.core.deployment import DeploymentConfig
from spot_deployer.utils.service_installer import ServiceInstaller


class TestServiceInstaller(unittest.TestCase):
    """Test ServiceInstaller functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)

        # Create test deployment structure
        self.spot_dir = self.test_dir / ".spot"
        self.spot_dir.mkdir()

        # Create services directory
        self.services_dir = self.spot_dir / "services"
        self.services_dir.mkdir()

        # Create test service files
        self.create_test_service(
            "webapp.service",
            """
[Unit]
Description=Web Application
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/app/server.py
Restart=always

[Install]
WantedBy=multi-user.target
""",
        )

        self.create_test_service(
            "worker.service",
            """
[Unit]
Description=Background Worker
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/app/worker.py
Restart=always

[Install]
WantedBy=multi-user.target
""",
        )

        # Mock SSH manager
        self.mock_ssh = MagicMock()
        self.mock_ui = MagicMock()

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def create_test_service(self, name: str, content: str):
        """Create a test service file."""
        service_file = self.services_dir / name
        service_file.write_text(content.strip())

    def test_collect_services_basic(self):
        """Test basic service collection."""
        config = DeploymentConfig(
            version=1,
            packages=[],
            scripts=[],
            uploads=[],
            services=["webapp.service"],
            spot_dir=self.spot_dir,
            services_dir=self.services_dir,
        )

        installer = ServiceInstaller(self.mock_ssh, self.mock_ui)
        services = installer.collect_services(config)

        self.assertEqual(len(services), 1)
        self.assertEqual(services[0]["name"], "webapp.service")
        self.assertIn("[Unit]", services[0]["content"])
        self.assertIn("Description=Web Application", services[0]["content"])

    def test_collect_services_multiple(self):
        """Test collecting multiple services."""
        config = DeploymentConfig(
            version=1,
            packages=[],
            scripts=[],
            uploads=[],
            services=["webapp.service", "worker.service"],
            spot_dir=self.spot_dir,
            services_dir=self.services_dir,
        )

        installer = ServiceInstaller(self.mock_ssh, self.mock_ui)
        services = installer.collect_services(config)

        self.assertEqual(len(services), 2)
        service_names = [s["name"] for s in services]
        self.assertIn("webapp.service", service_names)
        self.assertIn("worker.service", service_names)

    def test_collect_services_missing_file(self):
        """Test handling of missing service files."""
        config = DeploymentConfig(
            version=1,
            packages=[],
            scripts=[],
            uploads=[],
            services=["missing.service"],
            spot_dir=self.spot_dir,
            services_dir=self.services_dir,
        )

        installer = ServiceInstaller(self.mock_ssh, self.mock_ui)
        services = installer.collect_services(config)

        self.assertEqual(len(services), 0)

    def test_collect_services_with_disabled_suffix(self):
        """Test handling of .disabled service files."""
        # Create a disabled service
        self.create_test_service(
            "disabled.service.disabled",
            """
[Unit]
Description=Disabled Service

[Service]
Type=simple
ExecStart=/bin/true
""",
        )

        config = DeploymentConfig(
            version=1,
            packages=[],
            scripts=[],
            uploads=[],
            services=[],  # Empty services list
            spot_dir=self.spot_dir,
            services_dir=self.services_dir,
        )

        installer = ServiceInstaller(self.mock_ssh, self.mock_ui)
        services = installer.collect_services(config)

        # Should not collect disabled services
        self.assertEqual(len(services), 0)

    def test_install_services(self):
        """Test service installation process."""
        services = [
            {
                "name": "webapp.service",
                "content": "[Unit]\nDescription=Test\n[Service]\nExecStart=/bin/true",
            }
        ]

        installer = ServiceInstaller(self.mock_ssh, self.mock_ui)
        installer.install_services("1.2.3.4", services)

        # Verify SSH commands
        calls = self.mock_ssh.execute_command.call_args_list

        # Should create service file
        self.assertTrue(
            any("tee /etc/systemd/system/webapp.service" in str(call) for call in calls)
        )

        # Should reload systemd
        self.assertTrue(any("systemctl daemon-reload" in str(call) for call in calls))

        # Should enable service
        self.assertTrue(any("systemctl enable webapp.service" in str(call) for call in calls))

    def test_install_services_multiple(self):
        """Test installing multiple services."""
        services = [
            {
                "name": "webapp.service",
                "content": "[Unit]\nDescription=Web\n[Service]\nExecStart=/bin/true",
            },
            {
                "name": "worker.service",
                "content": "[Unit]\nDescription=Worker\n[Service]\nExecStart=/bin/true",
            },
        ]

        installer = ServiceInstaller(self.mock_ssh, self.mock_ui)
        installer.install_services("1.2.3.4", services)

        # Verify both services are installed
        calls = [str(call) for call in self.mock_ssh.execute_command.call_args_list]
        self.assertTrue(any("webapp.service" in call for call in calls))
        self.assertTrue(any("worker.service" in call for call in calls))

    def test_install_services_empty_list(self):
        """Test installation with empty service list."""
        installer = ServiceInstaller(self.mock_ssh, self.mock_ui)
        installer.install_services("1.2.3.4", [])

        # Should not execute any commands
        self.mock_ssh.execute_command.assert_not_called()

    def test_validate_services(self):
        """Test service validation."""
        config = DeploymentConfig(
            version=1,
            packages=[],
            scripts=[],
            uploads=[],
            services=["webapp.service", "missing.service"],
            spot_dir=self.spot_dir,
            services_dir=self.services_dir,
        )

        installer = ServiceInstaller(self.mock_ssh, self.mock_ui)
        errors = installer.validate_services(config)

        self.assertEqual(len(errors), 1)
        self.assertIn("missing.service", errors[0])

    def test_validate_service_content(self):
        """Test validation of service file content."""
        # Create invalid service file (missing [Unit] section)
        self.create_test_service(
            "invalid.service",
            """
[Service]
ExecStart=/bin/true
""",
        )

        config = DeploymentConfig(
            version=1,
            packages=[],
            scripts=[],
            uploads=[],
            services=["invalid.service"],
            spot_dir=self.spot_dir,
            services_dir=self.services_dir,
        )

        installer = ServiceInstaller(self.mock_ssh, self.mock_ui)
        errors = installer.validate_services(config)

        # Should detect missing [Unit] section
        self.assertEqual(len(errors), 1)
        self.assertIn("[Unit]", errors[0])


if __name__ == "__main__":
    unittest.main()
