"""Unit tests for deployment validation."""

import shutil
import tempfile
import unittest
from pathlib import Path

from spot_deployer.core.deployment import DeploymentConfig, DeploymentValidator


class TestDeploymentValidator(unittest.TestCase):
    """Test the deployment validation functionality."""

    def setUp(self):
        """Create a temporary directory for testing."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()
        import os

        os.chdir(self.test_dir)

    def tearDown(self):
        """Clean up temporary directory."""
        import os

        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    def test_check_missing_spot_directory(self):
        """Test validation when .spot directory is missing."""
        is_valid, missing = DeploymentValidator.check_spot_directory(Path.cwd())

        self.assertFalse(is_valid)
        self.assertIn(".spot", missing)
        self.assertIn(".spot/config.yaml", missing)
        self.assertIn(".spot/deployment.yaml", missing)

    def test_check_partial_spot_directory(self):
        """Test validation with partial .spot structure."""
        spot_dir = Path.cwd() / ".spot"
        spot_dir.mkdir()
        (spot_dir / "scripts").mkdir()

        is_valid, missing = DeploymentValidator.check_spot_directory(Path.cwd())

        self.assertFalse(is_valid)
        # These should be missing
        self.assertIn(".spot/config.yaml", missing)
        self.assertIn(".spot/services", missing)
        self.assertIn(".spot/configs", missing)
        self.assertIn(".spot/files", missing)

    def test_check_complete_spot_directory(self):
        """Test validation with complete .spot structure."""
        spot_dir = Path.cwd() / ".spot"
        spot_dir.mkdir()
        (spot_dir / "scripts").mkdir()
        (spot_dir / "services").mkdir()
        (spot_dir / "configs").mkdir()
        (spot_dir / "files").mkdir()

        # Create required files
        (spot_dir / "config.yaml").write_text(
            "aws:\n  ssh_key_name: test\nregions:\n  - us-west-2:"
        )
        (spot_dir / "deployment.yaml").write_text("version: 1\ndeployment:\n  packages: []")
        (spot_dir / "scripts" / "setup.sh").write_text("#!/bin/bash\necho test")
        (spot_dir / "scripts" / "additional_commands.sh").write_text("#!/bin/bash")

        is_valid, missing = DeploymentValidator.check_spot_directory(Path.cwd())

        self.assertTrue(is_valid)
        self.assertEqual(len(missing), 0)

    def test_validate_yaml_syntax_valid(self):
        """Test YAML syntax validation with valid file."""
        test_file = Path("test.yaml")
        test_file.write_text("key: value\nlist:\n  - item1\n  - item2")

        is_valid, error = DeploymentValidator.validate_yaml_syntax(test_file)

        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_validate_yaml_syntax_invalid(self):
        """Test YAML syntax validation with invalid file."""
        test_file = Path("test.yaml")
        # This is actually valid YAML (multiline string), use truly invalid YAML
        test_file.write_text("key: value\n bad:\n  - item\n    bad indent")

        is_valid, error = DeploymentValidator.validate_yaml_syntax(test_file)

        self.assertFalse(is_valid)
        self.assertIsNotNone(error)

    def test_validate_service_file_valid(self):
        """Test systemd service file validation with valid file."""
        service_file = Path("test.service")
        service_file.write_text("""[Unit]
Description=Test Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/app.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
""")

        is_valid, errors = DeploymentValidator.validate_service_file(service_file)

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_service_file_missing_sections(self):
        """Test service file validation with missing sections."""
        service_file = Path("test.service")
        service_file.write_text("""[Unit]
Description=Test Service

[Service]
Type=simple
""")

        is_valid, errors = DeploymentValidator.validate_service_file(service_file)

        self.assertFalse(is_valid)
        self.assertIn("Missing [Install] section", errors)
        self.assertIn("Missing ExecStart directive", errors)


class TestDeploymentConfig(unittest.TestCase):
    """Test the DeploymentConfig class."""

    def setUp(self):
        """Create a temporary directory with valid .spot structure."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()
        import os

        os.chdir(self.test_dir)

        # Create valid .spot structure
        self.spot_dir = Path.cwd() / ".spot"
        self.spot_dir.mkdir()
        (self.spot_dir / "scripts").mkdir()
        (self.spot_dir / "services").mkdir()
        (self.spot_dir / "configs").mkdir()
        (self.spot_dir / "files").mkdir()

        # Create config.yaml
        config_content = """aws:
  ssh_key_name: test-key
  total_instances: 1
regions:
  - us-west-2:
      machine_type: t3.micro
"""
        (self.spot_dir / "config.yaml").write_text(config_content)

        # Create deployment.yaml
        deployment_content = """version: 1
deployment:
  packages:
    - curl
    - git
  scripts:
    - name: setup
      path: scripts/setup.sh
      order: 1
  uploads: []
  services: []
"""
        (self.spot_dir / "deployment.yaml").write_text(deployment_content)

        # Create referenced script
        (self.spot_dir / "scripts" / "setup.sh").write_text("#!/bin/bash\necho setup")

    def tearDown(self):
        """Clean up temporary directory."""
        import os

        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    def test_from_spot_dir_success(self):
        """Test loading DeploymentConfig from valid .spot directory."""
        config = DeploymentConfig.from_spot_dir(self.spot_dir)

        self.assertEqual(config.version, 1)
        self.assertEqual(config.packages, ["curl", "git"])
        self.assertEqual(len(config.scripts), 1)
        self.assertEqual(config.scripts[0]["name"], "setup")

    def test_from_spot_dir_missing_deployment_yaml(self):
        """Test loading when deployment.yaml is missing."""
        (self.spot_dir / "deployment.yaml").unlink()

        with self.assertRaises(FileNotFoundError):
            DeploymentConfig.from_spot_dir(self.spot_dir)

    def test_validate_success(self):
        """Test validation of valid configuration."""
        config = DeploymentConfig.from_spot_dir(self.spot_dir)
        is_valid, errors = config.validate()

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_missing_script(self):
        """Test validation when referenced script is missing."""
        config = DeploymentConfig.from_spot_dir(self.spot_dir)
        # Add a script that doesn't exist
        config.scripts.append({"name": "missing", "path": "scripts/missing.sh"})

        is_valid, errors = config.validate()

        self.assertFalse(is_valid)
        self.assertTrue(any("Script not found" in e for e in errors))

    def test_validate_missing_ssh_key(self):
        """Test validation when SSH key is missing from config."""
        # Modify config.yaml to remove ssh_key_name
        config_content = """aws:
  total_instances: 1
regions:
  - us-west-2:
      machine_type: t3.micro
"""
        (self.spot_dir / "config.yaml").write_text(config_content)

        config = DeploymentConfig.from_spot_dir(self.spot_dir)
        is_valid, errors = config.validate()

        self.assertFalse(is_valid)
        self.assertTrue(any("ssh_key_name" in e for e in errors))

    def test_get_all_files(self):
        """Test getting all files to upload."""
        # Add a file to upload
        (self.spot_dir / "files" / "test.txt").write_text("test content")

        # Update deployment.yaml with uploads
        deployment_content = """version: 1
deployment:
  packages: []
  scripts:
    - name: setup
      path: scripts/setup.sh
  uploads:
    - source: files/test.txt
      dest: /opt/test.txt
  services: []
"""
        (self.spot_dir / "deployment.yaml").write_text(deployment_content)

        config = DeploymentConfig.from_spot_dir(self.spot_dir)
        files = config.get_all_files()

        self.assertIn(Path("scripts/setup.sh"), files)
        self.assertIn(Path("files/test.txt"), files)


if __name__ == "__main__":
    unittest.main()
