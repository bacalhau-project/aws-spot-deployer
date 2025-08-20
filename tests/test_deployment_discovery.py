#!/usr/bin/env python3
"""Unit tests for deployment discovery module."""

import shutil
import tempfile
import unittest
from pathlib import Path

from spot_deployer.core.deployment_discovery import DeploymentDiscovery, DeploymentMode


class TestDeploymentDiscovery(unittest.TestCase):
    """Test the deployment discovery functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_detect_portable_mode(self):
        """Test detection of portable deployment mode."""
        # Create .spot directory with deployment.yaml
        spot_dir = self.temp_dir / ".spot"
        spot_dir.mkdir()
        (spot_dir / "deployment.yaml").write_text("version: 1\n")

        discovery = DeploymentDiscovery(self.temp_dir)
        mode = discovery.detect_deployment_mode()

        self.assertEqual(mode, DeploymentMode.PORTABLE)

    def test_detect_convention_mode(self):
        """Test detection of convention-based deployment mode."""
        # Create deployment directory with setup.sh
        deployment_dir = self.temp_dir / "deployment"
        deployment_dir.mkdir()
        (deployment_dir / "setup.sh").write_text("#!/bin/bash\necho 'setup'\n")

        discovery = DeploymentDiscovery(self.temp_dir)
        mode = discovery.detect_deployment_mode()

        self.assertEqual(mode, DeploymentMode.CONVENTION)

    def test_detect_convention_mode_with_init(self):
        """Test detection of convention mode with init.sh."""
        # Create deployment directory with init.sh
        deployment_dir = self.temp_dir / "deployment"
        deployment_dir.mkdir()
        (deployment_dir / "init.sh").write_text("#!/bin/bash\necho 'init'\n")

        discovery = DeploymentDiscovery(self.temp_dir)
        mode = discovery.detect_deployment_mode()

        self.assertEqual(mode, DeploymentMode.CONVENTION)

    def test_detect_legacy_mode(self):
        """Test detection of legacy deployment mode."""
        # Create instance/scripts directory
        instance_dir = self.temp_dir / "instance"
        scripts_dir = instance_dir / "scripts"
        scripts_dir.mkdir(parents=True)

        discovery = DeploymentDiscovery(self.temp_dir)
        mode = discovery.detect_deployment_mode()

        self.assertEqual(mode, DeploymentMode.LEGACY)

    def test_detect_default_to_legacy(self):
        """Test that discovery defaults to legacy when no structure found."""
        discovery = DeploymentDiscovery(self.temp_dir)
        mode = discovery.detect_deployment_mode()

        self.assertEqual(mode, DeploymentMode.LEGACY)

    def test_find_project_root_with_spot(self):
        """Test finding project root with .spot directory."""
        spot_dir = self.temp_dir / ".spot"
        spot_dir.mkdir()

        # Create a subdirectory and search from there
        sub_dir = self.temp_dir / "sub" / "directory"
        sub_dir.mkdir(parents=True)

        discovery = DeploymentDiscovery(sub_dir)
        root = discovery.find_project_root()

        # Resolve both paths for comparison
        self.assertEqual(root.resolve(), self.temp_dir.resolve())

    def test_find_project_root_with_config(self):
        """Test finding project root with config.yaml."""
        (self.temp_dir / "config.yaml").write_text("aws:\n  key: value\n")

        # Create a subdirectory and search from there
        sub_dir = self.temp_dir / "sub"
        sub_dir.mkdir()

        discovery = DeploymentDiscovery(sub_dir)
        root = discovery.find_project_root()

        # Resolve both paths for comparison
        self.assertEqual(root.resolve(), self.temp_dir.resolve())

    def test_find_project_root_not_found(self):
        """Test when project root cannot be found."""
        # Create a deep directory with no markers
        deep_dir = self.temp_dir / "a" / "b" / "c" / "d" / "e" / "f"
        deep_dir.mkdir(parents=True)

        discovery = DeploymentDiscovery(deep_dir)
        root = discovery.find_project_root(max_depth=3)  # Limited depth

        self.assertIsNone(root)

    def test_validate_portable_structure_valid(self):
        """Test validation of valid portable structure."""
        spot_dir = self.temp_dir / ".spot"
        spot_dir.mkdir()
        (spot_dir / "deployment.yaml").write_text("version: 1\n")
        (spot_dir / "config.yaml").write_text("aws:\n  key: value\n")

        # Create optional directories
        (spot_dir / "scripts").mkdir()
        (spot_dir / "files").mkdir()
        (spot_dir / "services").mkdir()
        (spot_dir / "configs").mkdir()

        discovery = DeploymentDiscovery(self.temp_dir)
        is_valid, errors = discovery.validate_discovered_structure(
            DeploymentMode.PORTABLE, self.temp_dir
        )

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_portable_structure_missing_files(self):
        """Test validation of portable structure with missing required files."""
        spot_dir = self.temp_dir / ".spot"
        spot_dir.mkdir()
        # Only create deployment.yaml, not config.yaml

        (spot_dir / "deployment.yaml").write_text("version: 1\n")

        discovery = DeploymentDiscovery(self.temp_dir)
        is_valid, errors = discovery.validate_discovered_structure(
            DeploymentMode.PORTABLE, self.temp_dir
        )

        self.assertFalse(is_valid)
        self.assertEqual(len(errors), 1)
        self.assertIn("config.yaml", errors[0])

    def test_validate_convention_structure_valid(self):
        """Test validation of valid convention structure."""
        deployment_dir = self.temp_dir / "deployment"
        deployment_dir.mkdir()
        (deployment_dir / "setup.sh").write_text("#!/bin/bash\n")

        discovery = DeploymentDiscovery(self.temp_dir)
        is_valid, errors = discovery.validate_discovered_structure(
            DeploymentMode.CONVENTION, self.temp_dir
        )

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_convention_structure_no_setup(self):
        """Test validation of convention structure without setup script."""
        deployment_dir = self.temp_dir / "deployment"
        deployment_dir.mkdir()
        # No setup.sh or init.sh

        discovery = DeploymentDiscovery(self.temp_dir)
        is_valid, errors = discovery.validate_discovered_structure(
            DeploymentMode.CONVENTION, self.temp_dir
        )

        self.assertFalse(is_valid)
        self.assertEqual(len(errors), 1)
        self.assertIn("setup.sh or init.sh", errors[0])

    def test_get_deployment_config_portable(self):
        """Test getting deployment config for portable mode."""
        # Create valid portable structure
        spot_dir = self.temp_dir / ".spot"
        spot_dir.mkdir()

        deployment_yaml = """
version: 1
deployment:
  packages:
    - python3
"""
        (spot_dir / "deployment.yaml").write_text(deployment_yaml)
        (spot_dir / "config.yaml").write_text("aws:\n  key: value\n")

        # Create required directories
        (spot_dir / "scripts").mkdir()
        (spot_dir / "files").mkdir()
        (spot_dir / "services").mkdir()
        (spot_dir / "configs").mkdir()

        discovery = DeploymentDiscovery(self.temp_dir)
        config = discovery.get_deployment_config()

        self.assertIsNotNone(config)
        self.assertEqual(config.version, 1)
        self.assertEqual(config.packages, ["python3"])

    def test_get_deployment_config_no_root(self):
        """Test getting deployment config when no root found."""
        # Empty directory with no deployment markers
        discovery = DeploymentDiscovery(self.temp_dir)
        config = discovery.get_deployment_config()

        self.assertIsNone(config)


if __name__ == "__main__":
    unittest.main()
