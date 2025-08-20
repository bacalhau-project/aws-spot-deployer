#!/usr/bin/env python3
"""Unit tests for the generate command."""

import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from spot_deployer.commands.generate import create_file, generate_structure


class TestGenerateCommand(unittest.TestCase):
    """Test the generate command functionality."""

    def setUp(self):
        """Create a temporary directory for testing."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()
        # Change to test directory
        import os

        os.chdir(self.test_dir)

    def tearDown(self):
        """Clean up temporary directory."""
        import os

        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    def test_create_file_new(self):
        """Test creating a new file."""
        test_path = Path("test.txt")
        result = create_file(test_path, "test content")

        self.assertTrue(result)
        self.assertTrue(test_path.exists())
        self.assertEqual(test_path.read_text(), "test content")

    def test_create_file_skip_existing(self):
        """Test skipping existing files."""
        test_path = Path("existing.txt")
        test_path.write_text("original content")

        result = create_file(test_path, "new content", skip_existing=True)

        self.assertFalse(result)
        self.assertEqual(test_path.read_text(), "original content")

    def test_create_file_executable(self):
        """Test that .sh files are made executable."""
        test_path = Path("script.sh")
        create_file(test_path, "#!/bin/bash\necho test")

        self.assertTrue(test_path.exists())
        # Check if executable (owner execute permission)
        import stat

        self.assertTrue(test_path.stat().st_mode & stat.S_IXUSR)

    def test_generate_structure_creates_all_files(self):
        """Test that generate_structure creates all required files."""
        generate_structure(Path.cwd())

        spot_dir = Path.cwd() / ".spot"

        # Check directories exist
        self.assertTrue(spot_dir.exists())
        self.assertTrue((spot_dir / "scripts").exists())
        self.assertTrue((spot_dir / "services").exists())
        self.assertTrue((spot_dir / "configs").exists())
        self.assertTrue((spot_dir / "files").exists())

        # Check files exist
        self.assertTrue((spot_dir / "config.yaml").exists())
        self.assertTrue((spot_dir / "deployment.yaml").exists())
        self.assertTrue((spot_dir / "scripts" / "setup.sh").exists())
        self.assertTrue((spot_dir / "scripts" / "additional_commands.sh").exists())

    def test_generate_structure_valid_yaml(self):
        """Test that generated YAML files are valid."""
        generate_structure(Path.cwd())

        spot_dir = Path.cwd() / ".spot"

        # Test config.yaml
        with open(spot_dir / "config.yaml") as f:
            config = yaml.safe_load(f)
            self.assertIn("aws", config)
            self.assertIn("regions", config)
            self.assertEqual(config["aws"]["ssh_key_name"], "YOUR-SSH-KEY-NAME")

        # Test deployment.yaml
        with open(spot_dir / "deployment.yaml") as f:
            deployment = yaml.safe_load(f)
            self.assertIn("version", deployment)
            self.assertIn("deployment", deployment)
            self.assertIn("packages", deployment["deployment"])
            self.assertIn("scripts", deployment["deployment"])

    def test_generate_structure_idempotent(self):
        """Test that running generate twice doesn't overwrite files."""
        generate_structure(Path.cwd())

        # Modify a file
        spot_dir = Path.cwd() / ".spot"
        setup_script = spot_dir / "scripts" / "setup.sh"
        setup_script.write_text("# Modified content")

        # Run generate again
        generate_structure(Path.cwd())

        # Check that modified file wasn't overwritten
        self.assertEqual(setup_script.read_text(), "# Modified content")


if __name__ == "__main__":
    unittest.main()
