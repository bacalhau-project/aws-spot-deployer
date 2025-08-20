#!/usr/bin/env python3
"""Integration tests for create command with portable deployments."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from spot_deployer.commands.create import cmd_create
from spot_deployer.core.config import SimpleConfig
from spot_deployer.core.state import SimpleStateManager


class TestCreateIntegration(unittest.TestCase):
    """Test create command integration with portable deployments."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_path = Path(self.temp_dir.name)

        # Change to temp directory
        self.original_cwd = Path.cwd()
        import os

        os.chdir(self.test_path)

    def tearDown(self):
        """Clean up test environment."""
        import os

        os.chdir(self.original_cwd)
        self.temp_dir.cleanup()

    @patch("spot_deployer.commands.create.check_aws_auth")
    @patch("spot_deployer.commands.create.create_instances_in_region_with_table")
    def test_portable_deployment_detection(self, mock_create, mock_auth):
        """Test that portable deployment is detected and used."""
        # Setup mocks
        mock_auth.return_value = True
        mock_create.return_value = []

        # Create .spot directory structure
        spot_dir = self.test_path / ".spot"
        spot_dir.mkdir()

        # Create minimal config.yaml
        config_yaml = spot_dir / "config.yaml"
        config_yaml.write_text("""
aws:
  total_instances: 1
  username: ubuntu
  ssh_key_name: test-key
regions:
  - us-west-2:
      machine_type: t3.micro
""")

        # Create deployment.yaml
        deployment_yaml = spot_dir / "deployment.yaml"
        deployment_yaml.write_text("""
version: 1
packages:
  - nginx
scripts:
  - command: /opt/deployment/setup.sh
    working_dir: /opt/deployment
""")

        # Create mock config and state
        config = MagicMock()
        config.config_file = str(config_yaml)
        config.total_instances = MagicMock(return_value=1)
        config.regions = MagicMock(
            return_value=[{"region": "us-west-2", "count": 1, "machine_type": "t3.micro"}]
        )

        state = MagicMock()

        # Run create command
        with patch("spot_deployer.commands.create.ConfigValidator") as mock_validator:
            validator_instance = mock_validator.return_value
            validator_instance.validate_config_file.return_value = (True, [])

            with patch("spot_deployer.commands.create.rich_success") as mock_success:
                with patch("spot_deployer.commands.create.setup_logger"):
                    # This should detect portable deployment
                    cmd_create(config, state)

                    # Check that portable deployment was detected
                    mock_success.assert_any_call("✅ Using portable deployment (.spot directory)")

    @patch("spot_deployer.commands.create.check_aws_auth")
    @patch("spot_deployer.commands.create.create_instances_in_region_with_table")
    def test_convention_deployment_detection(self, mock_create, mock_auth):
        """Test that convention-based deployment is detected and used."""
        # Setup mocks
        mock_auth.return_value = True
        mock_create.return_value = []

        # Create deployment directory structure
        deployment_dir = self.test_path / "deployment"
        deployment_dir.mkdir()

        # Create setup.sh
        setup_script = deployment_dir / "setup.sh"
        setup_script.write_text("#!/bin/bash\necho 'setup'\n")

        # Create config.yaml in current directory
        config_yaml = self.test_path / "config.yaml"
        config_yaml.write_text("""
aws:
  total_instances: 1
  username: ubuntu
  ssh_key_name: test-key
regions:
  - us-west-2:
      machine_type: t3.micro
""")

        # Create mock config and state
        config = MagicMock()
        config.config_file = str(config_yaml)
        config.total_instances = MagicMock(return_value=1)
        config.regions = MagicMock(
            return_value=[{"region": "us-west-2", "count": 1, "machine_type": "t3.micro"}]
        )

        state = MagicMock()

        # Run create command
        with patch("spot_deployer.commands.create.ConfigValidator") as mock_validator:
            validator_instance = mock_validator.return_value
            validator_instance.validate_config_file.return_value = (True, [])

            with patch("spot_deployer.commands.create.rich_success") as mock_success:
                with patch("spot_deployer.commands.create.setup_logger"):
                    # This should detect convention deployment
                    cmd_create(config, state)

                    # Check that convention deployment was detected
                    mock_success.assert_any_call(
                        "✅ Using convention-based deployment (deployment/ directory)"
                    )

    @patch("spot_deployer.commands.create.check_aws_auth")
    @patch("spot_deployer.commands.create.create_instances_in_region_with_table")
    def test_legacy_deployment_fallback(self, mock_create, mock_auth):
        """Test that legacy deployment is used when no structure found."""
        # Setup mocks
        mock_auth.return_value = True
        mock_create.return_value = []

        # Create config.yaml only (no deployment structure)
        config_yaml = self.test_path / "config.yaml"
        config_yaml.write_text("""
aws:
  total_instances: 1
  username: ubuntu
  ssh_key_name: test-key
regions:
  - us-west-2:
      machine_type: t3.micro
""")

        # Create mock config and state
        config = MagicMock()
        config.config_file = str(config_yaml)
        config.total_instances = MagicMock(return_value=1)
        config.regions = MagicMock(
            return_value=[{"region": "us-west-2", "count": 1, "machine_type": "t3.micro"}]
        )

        state = MagicMock()

        # Run create command
        with patch("spot_deployer.commands.create.ConfigValidator") as mock_validator:
            validator_instance = mock_validator.return_value
            validator_instance.validate_config_file.return_value = (True, [])

            with patch("spot_deployer.commands.create.rich_warning") as mock_warning:
                with patch("spot_deployer.commands.create.setup_logger"):
                    # This should fall back to legacy mode
                    cmd_create(config, state)

                    # Check that warning was shown
                    mock_warning.assert_any_call(
                        "⚠️ No deployment structure found, using legacy mode"
                    )


if __name__ == "__main__":
    unittest.main()
