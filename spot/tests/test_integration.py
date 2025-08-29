"""Integration tests for the full workflow."""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestFullWorkflow(unittest.TestCase):
    """Test the complete generate -> validate -> create workflow."""

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

    def test_generate_validate_workflow(self):
        """Test that generate creates files that pass validation."""
        # Run generate command
        result = subprocess.run(
            [sys.executable, "-m", "spot_deployer", "generate"],
            capture_output=True,
            text=True,
            input="\n",  # Accept defaults
        )

        self.assertEqual(result.returncode, 0, f"Generate failed: {result.stderr}")

        # Import and test validation
        from spot_deployer.core.deployment import DeploymentConfig, DeploymentValidator

        # Check structure is valid
        is_valid, missing = DeploymentValidator.check_spot_directory(Path.cwd())
        self.assertTrue(is_valid, f"Generated structure invalid: {missing}")

        # Load and validate deployment config
        spot_dir = Path.cwd() / ".spot"
        config = DeploymentConfig.from_spot_dir(spot_dir)
        is_valid, errors = config.validate()

        # SSH key will be invalid placeholder, that's expected
        expected_errors = [e for e in errors if "YOUR-SSH-KEY-NAME" not in e]
        self.assertEqual(len(expected_errors), 0, f"Unexpected errors: {expected_errors}")

    def test_missing_spot_error_message(self):
        """Test that create command gives helpful error when .spot is missing."""
        # Try to run create without .spot directory
        from spot_deployer.core.deployment import DeploymentValidator

        is_valid, missing = DeploymentValidator.check_spot_directory(Path.cwd())

        self.assertFalse(is_valid)
        self.assertIn(".spot", missing)
        self.assertTrue(len(missing) > 5, "Should detect multiple missing items")

    def test_incremental_generation(self):
        """Test that generate doesn't overwrite existing files."""
        # First generation
        result = subprocess.run(
            [sys.executable, "-m", "spot_deployer", "generate"],
            capture_output=True,
            text=True,
            input="\n",
        )
        self.assertEqual(result.returncode, 0)

        # Modify a file
        setup_script = Path.cwd() / ".spot" / "scripts" / "setup.sh"
        original_content = "# Custom setup script"
        setup_script.write_text(original_content)

        # Second generation (should skip existing)
        result = subprocess.run(
            [sys.executable, "-m", "spot_deployer", "generate"],
            capture_output=True,
            text=True,
            input="y\n",  # Confirm to continue
        )
        self.assertEqual(result.returncode, 0)

        # Check file wasn't overwritten
        self.assertEqual(setup_script.read_text(), original_content)
        self.assertIn("Skipped", result.stdout)


if __name__ == "__main__":
    unittest.main()
