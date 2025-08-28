#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Quick smoke test for SkyPilot cluster deployment tool."""

import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def test_deployment_script() -> list[tuple[str, str]]:
    """Test deployment script basics."""
    errors = []

    script_path = Path("cluster-deploy")
    if not script_path.exists():
        errors.append(("cluster-deploy", "Main deployment script not found"))
        return errors

    # Check if script is executable
    if not os.access(script_path, os.X_OK):
        errors.append(("cluster-deploy", "Script is not executable"))

    # Test script syntax
    try:
        result = subprocess.run(
            ["bash", "-n", str(script_path)], capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            errors.append(("cluster-deploy", f"Syntax error: {result.stderr}"))
    except Exception as e:
        errors.append(("cluster-deploy", f"Failed to check syntax: {e}"))

    # Test help command (should not fail)
    try:
        result = subprocess.run(
            ["./cluster-deploy", "help"], capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            errors.append(
                ("cluster-deploy help", f"Help command failed: {result.stderr}")
            )
    except Exception as e:
        errors.append(("cluster-deploy help", f"Failed to run help: {e}"))

    return errors


def test_required_files() -> list[tuple[str, str]]:
    """Test that required files exist."""
    errors = []

    required_files = [
        "cluster.yaml",
        "README.md",
        "instance/config/bacalhau-config-template.yaml",
        "instance/config/sensor-config.yaml",
        "config/sensor-config.yaml",
        "compose/bacalhau-compose.yml",
        "compose/sensor-compose.yml",
        "scripts/generate_node_identity.py",
        "scripts/generate_bacalhau_config.py",
        "scripts/health_check.sh",
    ]

    for file_path in required_files:
        if not Path(file_path).exists():
            errors.append((file_path, "Required file not found"))

    return errors


def test_python_scripts() -> list[tuple[str, str]]:
    """Test Python script syntax."""
    errors = []

    python_scripts = [
        "scripts/generate_node_identity.py",
        "scripts/generate_bacalhau_config.py",
    ]

    for script in python_scripts:
        if not Path(script).exists():
            continue

        try:
            result = subprocess.run(
                ["python3", "-m", "py_compile", script],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                errors.append((script, f"Python syntax error: {result.stderr}"))
        except Exception as e:
            errors.append((script, f"Failed to check Python syntax: {e}"))

    return errors


def main() -> int:
    """Run all smoke tests."""
    quiet = "--quiet" in sys.argv

    if not quiet:
        print("🧪 Running SkyPilot deployment smoke tests...")

    all_errors = []

    # Run all tests
    test_functions = [
        ("Deployment Script", test_deployment_script),
        ("Required Files", test_required_files),
        ("Python Scripts", test_python_scripts),
    ]

    for test_name, test_func in test_functions:
        if not quiet:
            print(f"  • {test_name}...", end=" ", flush=True)

        try:
            errors = test_func()
            if errors:
                all_errors.extend(errors)
                if not quiet:
                    print(f"❌ ({len(errors)} errors)")
            else:
                if not quiet:
                    print("✅")
        except Exception as e:
            error_msg = f"Test function failed: {e}"
            all_errors.append((test_name, error_msg))
            if not quiet:
                print(f"❌ {error_msg}")

    # Report results
    if all_errors:
        if not quiet:
            print(f"\n❌ {len(all_errors)} errors found:")
            for module, error in all_errors:
                print(f"  - {module}: {error}")
        else:
            # For quiet mode, print to stderr so pre-commit can capture it
            print("❌ Smoke test failures:", file=sys.stderr)
            for module, error in all_errors:
                print(f"  - {module}: {error}", file=sys.stderr)
        return 1
    else:
        if not quiet:
            print("\n✅ All smoke tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
