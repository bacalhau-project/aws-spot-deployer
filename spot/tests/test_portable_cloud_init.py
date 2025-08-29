"""Tests for the portable cloud-init generator."""

import tempfile
import unittest
from pathlib import Path

from spot_deployer.core.deployment import DeploymentConfig
from spot_deployer.utils.portable_cloud_init import (
    CloudInitBuilder,
    PortableCloudInitGenerator,
)


class TestPortableCloudInitGenerator(unittest.TestCase):
    """Test portable cloud-init generator functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_path = Path(self.temp_dir.name)

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_generate_empty_config(self):
        """Test generating cloud-init with empty deployment config."""
        config = DeploymentConfig(version=1, packages=[], scripts=[], uploads=[], services=[])

        generator = PortableCloudInitGenerator(config)
        cloud_init = generator.generate()

        self.assertIn("#cloud-config", cloud_init)
        self.assertIn("users:", cloud_init)
        self.assertIn("ubuntu", cloud_init)

    def test_generate_with_packages(self):
        """Test generating cloud-init with packages."""
        config = DeploymentConfig(
            version=1, packages=["nginx", "python3", "git"], scripts=[], uploads=[], services=[]
        )

        generator = PortableCloudInitGenerator(config)
        cloud_init = generator.generate()

        self.assertIn("packages:", cloud_init)
        self.assertIn("- nginx", cloud_init)
        self.assertIn("- python3", cloud_init)
        self.assertIn("- git", cloud_init)

    def test_generate_with_scripts(self):
        """Test generating cloud-init with scripts."""
        config = DeploymentConfig(
            version=1,
            packages=[],
            scripts=[
                {"command": "/opt/deployment/setup.sh", "working_dir": "/opt/deployment"},
                {"command": "/opt/deployment/start.sh", "working_dir": "/opt"},
            ],
            uploads=[],
            services=[],
        )

        generator = PortableCloudInitGenerator(config)
        cloud_init = generator.generate()

        self.assertIn("runcmd:", cloud_init)
        # The new approach has a deploy script that handles setup.sh/init.sh
        self.assertIn("/opt/deploy.sh", cloud_init)
        self.assertIn("setup.sh", cloud_init)  # Referenced in the deploy script

    def test_generate_with_uploads(self):
        """Test generating cloud-init with upload permissions."""
        config = DeploymentConfig(
            version=1,
            packages=[],
            scripts=[],
            uploads=[
                {"source": "/local/path", "destination": "/opt/deployment", "permissions": "755"},
                {"source": "/secrets", "destination": "/opt/secrets", "permissions": "600"},
            ],
            services=[],
        )

        generator = PortableCloudInitGenerator(config)
        cloud_init = generator.generate()

        # Permissions are handled during SSH file upload now, not in cloud-init
        self.assertIn("/opt/deploy.sh", cloud_init)
        self.assertIn("mkdir -p /opt/deployment", cloud_init)

    def test_generate_with_services(self):
        """Test generating cloud-init with service files."""
        # Create a test service file
        service_file = self.test_path / "test.service"
        service_file.write_text("""[Unit]
Description=Test Service

[Service]
ExecStart=/usr/bin/test

[Install]
WantedBy=multi-user.target
""")

        config = DeploymentConfig(
            version=1, packages=[], scripts=[], uploads=[], services=[{"path": str(service_file)}]
        )

        generator = PortableCloudInitGenerator(config)
        cloud_init = generator.generate()

        self.assertIn("write_files:", cloud_init)
        # Services are uploaded separately now, not embedded in cloud-init
        self.assertIn("/opt/deploy.sh", cloud_init)
        # The deploy script is created
        self.assertIn("Portable deployment", cloud_init)

    def test_generate_creates_directories(self):
        """Test that cloud-init creates necessary directories."""
        config = DeploymentConfig(version=1, packages=[], scripts=[], uploads=[], services=[])

        generator = PortableCloudInitGenerator(config)
        cloud_init = generator.generate()

        self.assertIn("mkdir -p /opt/deployment", cloud_init)
        self.assertIn("mkdir -p /opt/configs", cloud_init)
        self.assertIn("mkdir -p /opt/files", cloud_init)
        self.assertIn("mkdir -p /opt/secrets", cloud_init)
        self.assertIn("mkdir -p /opt/uploaded_files", cloud_init)

    def test_generate_comprehensive_config(self):
        """Test generating cloud-init with all components."""
        # Create a service file
        service_file = self.test_path / "app.service"
        service_file.write_text("[Unit]\nDescription=App\n")

        config = DeploymentConfig(
            version=1,
            packages=["docker.io", "python3"],
            scripts=[{"command": "/opt/deployment/install.sh", "working_dir": "/opt/deployment"}],
            uploads=[{"source": "/app", "destination": "/opt/app", "permissions": "755"}],
            services=[{"path": str(service_file)}],
        )

        generator = PortableCloudInitGenerator(config)
        cloud_init = generator.generate()

        # Check all sections are present
        self.assertIn("#cloud-config", cloud_init)
        self.assertIn("packages:", cloud_init)
        self.assertIn("users:", cloud_init)
        self.assertIn("write_files:", cloud_init)
        self.assertIn("runcmd:", cloud_init)

        # Check specific content
        self.assertIn("docker.io", cloud_init)
        # Scripts are now executed by the deploy script, not directly in cloud-init
        self.assertIn("/opt/deploy.sh", cloud_init)
        # Service files are uploaded, not embedded
        self.assertIn("Portable deployment", cloud_init)

    def test_validate_valid_config(self):
        """Test validation of valid configuration."""
        config = DeploymentConfig(
            version=1,
            packages=["nginx"],
            scripts=[{"command": "/opt/deployment/setup.sh", "working_dir": "/opt"}],
            uploads=[{"source": "/local", "destination": "/opt/deployment", "permissions": "755"}],
            services=[],
        )

        generator = PortableCloudInitGenerator(config)
        is_valid, errors = generator.validate()

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_too_many_packages(self):
        """Test validation with too many packages."""
        config = DeploymentConfig(
            version=1,
            packages=[f"package{i}" for i in range(150)],  # 150 packages
            scripts=[],
            uploads=[],
            services=[],
        )

        generator = PortableCloudInitGenerator(config)
        is_valid, errors = generator.validate()

        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
        self.assertIn("Too many packages", errors[0])

    def test_validate_relative_script_paths(self):
        """Test validation catches relative script paths."""
        config = DeploymentConfig(
            version=1,
            packages=[],
            scripts=[
                {"command": "scripts/setup.sh", "working_dir": "/opt"}  # Relative path
            ],
            uploads=[],
            services=[],
        )

        generator = PortableCloudInitGenerator(config)
        is_valid, errors = generator.validate()

        self.assertFalse(is_valid)
        self.assertIn("absolute path", errors[0])

    def test_validate_missing_service_files(self):
        """Test validation catches missing service files."""
        config = DeploymentConfig(
            version=1,
            packages=[],
            scripts=[],
            uploads=[],
            services=[{"path": "/nonexistent/service.service"}],
        )

        generator = PortableCloudInitGenerator(config)
        is_valid, errors = generator.validate()

        self.assertFalse(is_valid)
        self.assertIn("Service file not found", errors[0])

    def test_validate_relative_upload_paths(self):
        """Test validation catches relative upload destination paths."""
        config = DeploymentConfig(
            version=1,
            packages=[],
            scripts=[],
            uploads=[
                {
                    "source": "/local",
                    "destination": "opt/deployment",
                    "permissions": "755",
                }  # Relative
            ],
            services=[],
        )

        generator = PortableCloudInitGenerator(config)
        is_valid, errors = generator.validate()

        self.assertFalse(is_valid)
        self.assertIn("absolute path", errors[0])

    def test_generate_with_template(self):
        """Test generating cloud-init with a template file."""
        # Create a template
        template_file = self.test_path / "template.yaml"
        template_file.write_text("""#cloud-config

packages:
{{PACKAGES}}

runcmd:
{{SCRIPTS}}
  - echo 'From template'
""")

        config = DeploymentConfig(
            version=1,
            packages=["nginx", "git"],
            scripts=[{"command": "/opt/setup.sh", "working_dir": "/opt"}],
            uploads=[],
            services=[],
        )

        generator = PortableCloudInitGenerator(config)
        cloud_init = generator.generate_with_template(template_file)

        self.assertIn("nginx", cloud_init)
        self.assertIn("git", cloud_init)
        self.assertIn("/opt/setup.sh", cloud_init)
        self.assertIn("From template", cloud_init)

    def test_generate_with_missing_template(self):
        """Test that missing template falls back to regular generation."""
        config = DeploymentConfig(
            version=1, packages=["nginx"], scripts=[], uploads=[], services=[]
        )

        generator = PortableCloudInitGenerator(config)
        cloud_init = generator.generate_with_template(Path("/nonexistent/template.yaml"))

        # Should fall back to regular generation
        self.assertIn("#cloud-config", cloud_init)
        self.assertIn("nginx", cloud_init)

    def test_script_error_handling(self):
        """Test that scripts have error handling."""
        config = DeploymentConfig(
            version=1,
            packages=[],
            scripts=[{"command": "/opt/may-fail.sh", "working_dir": "/opt"}],
            uploads=[],
            services=[],
        )

        generator = PortableCloudInitGenerator(config)
        cloud_init = generator.generate()

        # The deploy script has set -e for error handling
        self.assertIn("set -e", cloud_init)

    def test_yaml_escaping(self):
        """Test that special characters in commands are escaped."""
        config = DeploymentConfig(
            version=1,
            packages=[],
            scripts=[{"command": "/opt/script.sh 'with quotes'", "working_dir": "/opt"}],
            uploads=[],
            services=[],
        )

        generator = PortableCloudInitGenerator(config)
        cloud_init = generator.generate()

        # Single quotes should be escaped in YAML
        self.assertIn("''", cloud_init)  # Escaped quotes

    def test_deployment_marker_files(self):
        """Test that deployment marker files are created."""
        config = DeploymentConfig(version=1, packages=[], scripts=[], uploads=[], services=[])

        generator = PortableCloudInitGenerator(config)
        cloud_init = generator.generate()

        self.assertIn("/opt/deployment.marker", cloud_init)
        self.assertIn("/opt/deployment.complete", cloud_init)
        # The new minimal approach has "Deployment completed" in the deploy script
        self.assertIn("Deployment completed", cloud_init)


class TestCloudInitBuilder(unittest.TestCase):
    """Test CloudInitBuilder builder pattern."""

    def test_empty_builder(self):
        """Test building empty cloud-init."""
        builder = CloudInitBuilder()
        cloud_init = builder.build()

        self.assertEqual(cloud_init, "#cloud-config")

    def test_add_single_package(self):
        """Test adding a single package."""
        builder = CloudInitBuilder()
        cloud_init = builder.add_package("nginx").build()

        self.assertIn("packages:", cloud_init)
        self.assertIn("- nginx", cloud_init)

    def test_add_multiple_packages(self):
        """Test adding multiple packages."""
        builder = CloudInitBuilder()
        cloud_init = builder.add_packages(["nginx", "python3", "git"]).build()

        self.assertIn("- nginx", cloud_init)
        self.assertIn("- python3", cloud_init)
        self.assertIn("- git", cloud_init)

    def test_add_file(self):
        """Test adding a file."""
        builder = CloudInitBuilder()
        cloud_init = builder.add_file(
            "/etc/myapp.conf", "server {\n  listen 80;\n}", "0644"
        ).build()

        self.assertIn("write_files:", cloud_init)
        self.assertIn("/etc/myapp.conf", cloud_init)
        self.assertIn("server {", cloud_init)
        self.assertIn("listen 80;", cloud_init)

    def test_add_single_command(self):
        """Test adding a single command."""
        builder = CloudInitBuilder()
        cloud_init = builder.add_command("echo 'Hello World'").build()

        self.assertIn("runcmd:", cloud_init)
        self.assertIn("Hello World", cloud_init)

    def test_add_multiple_commands(self):
        """Test adding multiple commands."""
        builder = CloudInitBuilder()
        cloud_init = builder.add_commands(
            ["apt-get update", "apt-get install -y nginx", "systemctl start nginx"]
        ).build()

        self.assertIn("apt-get update", cloud_init)
        self.assertIn("apt-get install -y nginx", cloud_init)
        self.assertIn("systemctl start nginx", cloud_init)

    def test_builder_chaining(self):
        """Test method chaining in builder."""
        cloud_init = (
            CloudInitBuilder()
            .add_package("nginx")
            .add_package("python3")
            .add_file("/etc/test.conf", "config", "0644")
            .add_command("systemctl start nginx")
            .build()
        )

        self.assertIn("nginx", cloud_init)
        self.assertIn("python3", cloud_init)
        self.assertIn("/etc/test.conf", cloud_init)
        self.assertIn("systemctl start nginx", cloud_init)

    def test_comprehensive_builder(self):
        """Test building comprehensive cloud-init."""
        cloud_init = (
            CloudInitBuilder()
            .add_packages(["docker.io", "python3", "git"])
            .add_file("/opt/app/config.json", '{"key": "value"}', "0600")
            .add_file("/etc/systemd/system/app.service", "[Unit]\nDescription=App", "0644")
            .add_commands(
                [
                    "mkdir -p /opt/app",
                    "cd /opt/app",
                    "git clone https://github.com/example/app.git .",
                    "systemctl daemon-reload",
                    "systemctl enable app.service",
                    "systemctl start app.service",
                ]
            )
            .build()
        )

        # Check structure
        self.assertIn("#cloud-config", cloud_init)
        self.assertIn("packages:", cloud_init)
        self.assertIn("write_files:", cloud_init)
        self.assertIn("runcmd:", cloud_init)

        # Check content
        self.assertIn("docker.io", cloud_init)
        self.assertIn("config.json", cloud_init)
        self.assertIn("app.service", cloud_init)
        self.assertIn("git clone", cloud_init)


if __name__ == "__main__":
    unittest.main()
