"""Unit tests for ConfigValidator."""

import os
import tempfile
from unittest.mock import patch

from spot_deployer.utils.config_validator import ConfigValidator


class TestConfigValidator:
    """Test cases for ConfigValidator."""

    def test_initialization(self):
        """Test validator initialization."""
        validator = ConfigValidator()
        assert validator.errors == []
        assert validator.warnings == []

    def test_validate_missing_file(self):
        """Test validation of non-existent file."""
        validator = ConfigValidator()
        is_valid, config = validator.validate_config_file("/nonexistent/config.yaml")

        assert is_valid is False
        assert config == {}
        assert len(validator.errors) == 1
        assert "not found" in validator.errors[0]

    def test_validate_invalid_yaml(self):
        """Test validation of invalid YAML syntax."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: syntax: here")
            f.flush()

            validator = ConfigValidator()
            is_valid, config = validator.validate_config_file(f.name)

            os.unlink(f.name)

            assert is_valid is False
            assert "Invalid YAML syntax" in validator.errors[0]

    def test_validate_minimal_valid_config(self):
        """Test validation of minimal valid configuration."""
        config_content = """
aws:
  total_instances: 2
  username: ubuntu
regions:
  - us-west-2:
      machine_type: t3.micro
      image: auto
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            f.flush()

            validator = ConfigValidator()
            is_valid, config = validator.validate_config_file(f.name)

            os.unlink(f.name)

            assert is_valid is True
            assert len(validator.errors) == 0
            # Should have warning about missing SSH key
            assert any("public_ssh_key_path" in w for w in validator.warnings)

    def test_validate_missing_required_sections(self):
        """Test validation catches missing required sections."""
        config_content = """
aws:
  username: ubuntu
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            f.flush()

            validator = ConfigValidator()
            is_valid, config = validator.validate_config_file(f.name)

            os.unlink(f.name)

            assert is_valid is False
            # Should have errors for missing total_instances and regions
            assert any("total_instances" in e for e in validator.errors)
            assert any("regions" in e for e in validator.errors)

    def test_validate_invalid_instance_count(self):
        """Test validation of invalid instance counts."""
        test_cases = [
            ("negative", -1),
            ("string", "two"),
            ("float", 2.5),
        ]

        for test_name, value in test_cases:
            config_content = f"""
aws:
  total_instances: {value}
  username: ubuntu
regions:
  - us-west-2:
      machine_type: t3.micro
"""
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                f.write(config_content)
                f.flush()

                validator = ConfigValidator()
                is_valid, config = validator.validate_config_file(f.name)

                os.unlink(f.name)

                assert is_valid is False, f"Should be invalid for {test_name}"
                assert any(
                    "total_instances" in e and "positive integer" in e for e in validator.errors
                )

    def test_validate_zero_instances_warning(self):
        """Test that zero instances generates warning not error."""
        config_content = """
aws:
  total_instances: 0
  username: ubuntu
regions:
  - us-west-2:
      machine_type: t3.micro
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            f.flush()

            validator = ConfigValidator()
            is_valid, config = validator.validate_config_file(f.name)

            os.unlink(f.name)

            assert is_valid is True  # Valid but with warning
            assert any("total_instances' is 0" in w for w in validator.warnings)

    def test_validate_high_instance_count_warning(self):
        """Test that high instance count generates warning."""
        config_content = """
aws:
  total_instances: 150
  username: ubuntu
regions:
  - us-west-2:
      machine_type: t3.micro
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            f.flush()

            validator = ConfigValidator()
            is_valid, config = validator.validate_config_file(f.name)

            os.unlink(f.name)

            assert is_valid is True  # Valid but with warning
            assert any("expensive" in w for w in validator.warnings)

    def test_validate_ssh_keys(self, tmp_path):
        """Test SSH key validation."""
        # Create test SSH keys
        public_key = tmp_path / "id_test.pub"
        private_key = tmp_path / "id_test"

        public_key.write_text("ssh-rsa AAAA... test@example.com")
        private_key.write_text("-----BEGIN OPENSSH PRIVATE KEY-----")

        # Set correct permissions
        private_key.chmod(0o600)

        config_content = f"""
aws:
  total_instances: 1
  username: ubuntu
  public_ssh_key_path: {public_key}
  private_ssh_key_path: {private_key}
regions:
  - us-west-2:
      machine_type: t3.micro
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            f.flush()

            validator = ConfigValidator()
            is_valid, config = validator.validate_config_file(f.name)

            os.unlink(f.name)

            assert is_valid is True
            assert len(validator.errors) == 0

    def test_validate_ssh_key_permissions_warning(self, tmp_path):
        """Test warning for incorrect SSH key permissions."""
        private_key = tmp_path / "id_test"
        private_key.write_text("-----BEGIN OPENSSH PRIVATE KEY-----")

        # Set incorrect permissions
        private_key.chmod(0o644)

        config_content = f"""
aws:
  total_instances: 1
  username: ubuntu
  private_ssh_key_path: {private_key}
regions:
  - us-west-2:
      machine_type: t3.micro
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            f.flush()

            validator = ConfigValidator()
            is_valid, config = validator.validate_config_file(f.name)

            os.unlink(f.name)

            assert is_valid is True  # Still valid, just warning
            assert any("insecure permissions" in w for w in validator.warnings)
            assert any("chmod 600" in w for w in validator.warnings)

    def test_validate_regions(self):
        """Test region validation."""
        # Test with valid regions
        config_content = """
aws:
  total_instances: 1
  username: ubuntu
regions:
  - us-west-2:
      machine_type: t3.micro
  - eu-west-1:
      machine_type: t3.small
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            f.flush()

            validator = ConfigValidator()
            is_valid, config = validator.validate_config_file(f.name)

            os.unlink(f.name)

            assert is_valid is True

    def test_validate_duplicate_regions(self):
        """Test detection of duplicate regions."""
        config_content = """
aws:
  total_instances: 1
  username: ubuntu
regions:
  - us-west-2:
      machine_type: t3.micro
  - us-west-2:
      machine_type: t3.small
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            f.flush()

            validator = ConfigValidator()
            is_valid, config = validator.validate_config_file(f.name)

            os.unlink(f.name)

            assert is_valid is False
            assert any("Duplicate region" in e for e in validator.errors)

    def test_validate_unknown_region_warning(self):
        """Test warning for unknown regions."""
        config_content = """
aws:
  total_instances: 1
  username: ubuntu
regions:
  - mars-west-1:
      machine_type: t3.micro
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            f.flush()

            validator = ConfigValidator()
            is_valid, config = validator.validate_config_file(f.name)

            os.unlink(f.name)

            assert is_valid is True  # Valid but with warning
            assert any("Unknown AWS region" in w for w in validator.warnings)

    def test_validate_missing_machine_type(self):
        """Test error for missing machine type."""
        config_content = """
aws:
  total_instances: 1
  username: ubuntu
regions:
  - us-west-2:
      image: auto
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            f.flush()

            validator = ConfigValidator()
            is_valid, config = validator.validate_config_file(f.name)

            os.unlink(f.name)

            assert is_valid is False
            assert any("Missing 'machine_type'" in e for e in validator.errors)

    def test_validate_runtime_environment_no_aws(self):
        """Test runtime environment validation without AWS credentials."""
        validator = ConfigValidator()

        with patch("boto3.client") as mock_client:
            mock_client.side_effect = Exception("No credentials")

            is_valid = validator.validate_runtime_environment()

            assert is_valid is False

    def test_command_exists(self):
        """Test command existence checking."""
        validator = ConfigValidator()

        # Python should always exist
        assert validator._command_exists("python") or validator._command_exists("python3")

        # Non-existent command
        assert not validator._command_exists("definitely-not-a-real-command-12345")
