"""Tests for template system integration."""

import tempfile
import unittest
from pathlib import Path

from spot_deployer.core.deployment import DeploymentConfig
from spot_deployer.utils.portable_cloud_init import PortableCloudInitGenerator


class TestTemplateIntegration(unittest.TestCase):
    """Test template system integration with portable cloud-init."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_path = Path(self.temp_dir.name)

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_deployment_config_with_template(self):
        """Test that deployment config supports template field."""
        config = DeploymentConfig(
            version=1, packages=["nginx"], scripts=[], uploads=[], services=[], template="minimal"
        )

        self.assertEqual(config.template, "minimal")

    def test_generator_with_library_template(self):
        """Test generator using a library template."""
        config = DeploymentConfig(
            version=1, packages=["nginx"], scripts=[], uploads=[], services=[], template="minimal"
        )

        generator = PortableCloudInitGenerator(config)
        cloud_init = generator.generate_with_template(template_name="minimal")

        self.assertIn("#cloud-config", cloud_init)
        self.assertIn("Minimal deployment complete", cloud_init)
        self.assertIn("nginx", cloud_init)

    def test_generator_with_custom_template_file(self):
        """Test generator using a custom template file."""
        template_file = self.test_path / "custom.yaml"
        template_file.write_text("""#cloud-config
# Custom template
packages:
{{PACKAGES}}

runcmd:
  - echo "Custom deployment"
""")

        config = DeploymentConfig(
            version=1, packages=["docker"], scripts=[], uploads=[], services=[]
        )

        generator = PortableCloudInitGenerator(config)
        cloud_init = generator.generate_with_template(template_path=template_file)

        self.assertIn("Custom deployment", cloud_init)
        self.assertIn("docker", cloud_init)

    def test_generator_fallback_to_default(self):
        """Test generator falls back to default when template not found."""
        config = DeploymentConfig(
            version=1, packages=["nginx"], scripts=[], uploads=[], services=[]
        )

        generator = PortableCloudInitGenerator(config)
        # Try to use a non-existent template
        cloud_init = generator.generate_with_template(template_name="nonexistent")

        # Should fall back to default generation
        self.assertIn("#cloud-config", cloud_init)
        self.assertIn("nginx", cloud_init)

    def test_deployment_yaml_with_template(self):
        """Test loading deployment.yaml with template specified."""
        spot_dir = self.test_path / ".spot"
        spot_dir.mkdir()

        # Create config.yaml
        (spot_dir / "config.yaml").write_text("""
aws:
  total_instances: 1
""")

        # Create deployment.yaml with template
        (spot_dir / "deployment.yaml").write_text("""
version: 1
deployment:
  packages:
    - nginx
  template: docker
""")

        config = DeploymentConfig.from_spot_dir(spot_dir)

        self.assertEqual(config.template, "docker")
        self.assertEqual(config.packages, ["nginx"])


if __name__ == "__main__":
    unittest.main()
