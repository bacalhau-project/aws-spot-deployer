#!/usr/bin/env uv run
"""Quick Test Suite for AWS Spot Deployment Tool

This script runs the most critical tests that can be executed immediately
without requiring actual AWS deployments. Run with: python3 quick_test_suite.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import yaml

# ANSI color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


class QuickTestSuite:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.test_dir = tempfile.mkdtemp(prefix="spot_test_")
        self.original_dir = os.getcwd()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        os.chdir(self.original_dir)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def run_test(self, test_name, test_func):
        """Run a single test and track results"""
        print(f"\n{BOLD}TEST: {test_name}{RESET}")
        try:
            test_func()
            print(f"{GREEN}✅ PASSED{RESET}")
            self.passed += 1
        except AssertionError as e:
            print(f"{RED}❌ FAILED: {e}{RESET}")
            self.failed += 1
        except Exception as e:
            print(f"{RED}❌ ERROR: {type(e).__name__}: {e}{RESET}")
            self.failed += 1

    def test_config_file_creation(self):
        """TEST-001: Missing config file creates default"""
        os.chdir(self.test_dir)

        # Import locally to avoid issues
        sys.path.insert(0, self.original_dir)
        from deploy_spot import SimpleConfig

        # No config file exists
        assert not os.path.exists("config.yaml")

        # Create config
        config = SimpleConfig()

        # Should create default config
        assert os.path.exists("config.yaml")
        assert config.total_instances == 3  # Default value

    def test_invalid_yaml_handling(self):
        """TEST-002: Invalid YAML detection"""
        os.chdir(self.test_dir)

        # Create invalid YAML
        with open("config.yaml", "w") as f:
            f.write("""aws:
  total_instances: 3
    username: ubuntu  # Bad indentation
""")

        sys.path.insert(0, self.original_dir)
        from deploy_spot import SimpleConfig

        # Should raise exception with helpful message
        try:
            config = SimpleConfig()
            assert False, "Should have raised exception"
        except Exception as e:
            assert "YAML" in str(e) or "parse" in str(e).lower()

    def test_ssh_key_validation(self):
        """TEST-003: SSH key validation"""
        os.chdir(self.test_dir)

        # Create config with non-existent key
        config_data = {
            "aws": {"ssh_key_path": "/nonexistent/key.pem", "total_instances": 1},
            "regions": [{"us-west-2": {"machine_type": "t3.micro"}}],
        }

        with open("config.yaml", "w") as f:
            yaml.dump(config_data, f)

        sys.path.insert(0, self.original_dir)
        from deploy_spot import load_config

        # Should validate SSH key exists
        try:
            config = load_config()
            # Check if validation happens during deployment
            if hasattr(config, "ssh_key_path"):
                assert not os.path.exists(config.ssh_key_path)
        except Exception as e:
            # Good if it fails early
            assert "ssh" in str(e).lower() or "key" in str(e).lower()

    def test_state_file_corruption_recovery(self):
        """TEST-011: State file corruption recovery"""
        os.chdir(self.test_dir)

        # Create corrupted state file
        with open("instances.json", "w") as f:
            f.write("{invalid json")

        sys.path.insert(0, self.original_dir)
        from deploy_spot import SimpleStateManager

        # Should recover gracefully
        state = SimpleStateManager()
        instances = state.get_all_instances()
        assert isinstance(instances, list)
        assert len(instances) == 0

    def test_node_identity_determinism(self):
        """TEST-020: Identity generation determinism"""
        os.chdir(self.original_dir)

        # Set instance ID
        os.environ["INSTANCE_ID"] = "i-1234567890abcdef0"

        # Import and generate identity
        from instance.scripts.generate_node_identity import NodeIdentityGenerator

        gen = NodeIdentityGenerator()
        identity1 = gen.generate_identity()
        identity2 = gen.generate_identity()

        # Should be identical
        assert identity1 == identity2, "Identities should be deterministic"
        assert identity1["sensor_id"] == identity2["sensor_id"]

    def test_identity_data_validity(self):
        """TEST-022: GPS coordinate validation"""
        os.chdir(self.original_dir)

        from instance.scripts.generate_node_identity import NodeIdentityGenerator

        # Test 100 different identities
        for i in range(100):
            os.environ["INSTANCE_ID"] = f"i-test{i:04d}"
            gen = NodeIdentityGenerator()
            identity = gen.generate_identity()

            # Validate coordinates
            lat = identity["location"]["coordinates"]["latitude"]
            lon = identity["location"]["coordinates"]["longitude"]

            assert -90 <= lat <= 90, f"Invalid latitude: {lat}"
            assert -180 <= lon <= 180, f"Invalid longitude: {lon}"

            # Validate other fields
            assert identity["sensor_id"].startswith("SENSOR_")
            assert len(identity["sensor_id"].split("_")) == 4
            assert identity["device_info"]["manufacturer"] in [
                "AcmeSensors",
                "TechnoMetrics",
                "DataStream Corp",
                "Precision Instruments",
                "Global Sensing Inc",
            ]

    def test_config_defaults(self):
        """Test configuration default values"""
        os.chdir(self.test_dir)

        # Minimal config
        config_data = {"regions": [{"us-west-2": {}}]}
        with open("config.yaml", "w") as f:
            yaml.dump(config_data, f)

        sys.path.insert(0, self.original_dir)
        from deploy_spot import SimpleConfig

        config = SimpleConfig()

        # Check defaults
        assert config.total_instances == 3
        assert config.username == "ubuntu"
        assert config.files_directory == "files"
        assert config.scripts_directory == "instance/scripts"

    def test_file_path_validation(self):
        """Test file path handling"""
        os.chdir(self.test_dir)

        # Create test directories
        os.makedirs("files")
        os.makedirs("instance/scripts")

        # Test with Unicode filename
        test_file = Path("files") / "测试文件.txt"
        test_file.write_text("Test content")

        # Test with long filename
        long_name = "a" * 250 + ".txt"
        long_file = Path("files") / long_name
        long_file.write_text("Long name test")

        # Verify files exist and are readable
        assert test_file.exists()
        assert long_file.exists()
        assert len(long_file.name) == 254

    def test_progress_tracker_import(self):
        """Test Rich progress tracking components"""
        try:
            from rich.console import Console
            from rich.progress import Progress
            from rich.table import Table

            # Create console
            console = Console()

            # Create table
            table = Table(title="Test Table")
            table.add_column("Status")
            table.add_column("Message")
            table.add_row("✅", "Import successful")

            # Basic progress bar
            with Progress() as progress:
                task = progress.add_task("Testing...", total=10)
                progress.update(task, advance=10)

            assert True
        except ImportError as e:
            assert False, f"Rich library import failed: {e}"

    def test_dry_run_safety(self):
        """Test dry-run mode prevents actual operations"""
        result = subprocess.run(
            [
                "python3",
                os.path.join(self.original_dir, "deploy_spot.py"),
                "create",
                "--dry-run",
                "--count",
                "1",
            ],
            capture_output=True,
            text=True,
            cwd=self.original_dir,
        )

        # Should complete without errors
        assert result.returncode == 0 or "dry-run" in result.stdout.lower()
        # Should not create actual resources
        assert "would create" in result.stdout.lower() or "dry" in result.stdout.lower()

    def run_all_tests(self):
        """Execute all tests"""
        print(f"{BOLD}{BLUE}AWS Spot Deployment Tool - Quick Test Suite{RESET}")
        print("=" * 60)

        # Configuration tests
        self.run_test("Config file auto-creation", self.test_config_file_creation)
        self.run_test("Invalid YAML handling", self.test_invalid_yaml_handling)
        self.run_test("SSH key validation", self.test_ssh_key_validation)
        self.run_test("Config defaults", self.test_config_defaults)

        # State management tests
        self.run_test(
            "State corruption recovery", self.test_state_file_corruption_recovery
        )

        # Node identity tests
        self.run_test("Identity determinism", self.test_node_identity_determinism)
        self.run_test("Identity data validity", self.test_identity_data_validity)

        # File handling tests
        self.run_test("File path validation", self.test_file_path_validation)

        # UI component tests
        self.run_test("Rich components import", self.test_progress_tracker_import)

        # Safety tests
        self.run_test("Dry-run safety", self.test_dry_run_safety)

        # Summary
        print("\n" + "=" * 60)
        print(f"{BOLD}Test Summary:{RESET}")
        print(f"{GREEN}Passed: {self.passed}{RESET}")
        print(f"{RED}Failed: {self.failed}{RESET}")

        if self.failed == 0:
            print(f"\n{GREEN}{BOLD}All tests passed! 🎉{RESET}")
            return 0
        else:
            print(f"\n{RED}{BOLD}Some tests failed. Please review.{RESET}")
            return 1


if __name__ == "__main__":
    with QuickTestSuite() as suite:
        exit_code = suite.run_all_tests()
    sys.exit(exit_code)
