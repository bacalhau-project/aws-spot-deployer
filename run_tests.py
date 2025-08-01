#!/usr/bin/env python3
# /// script
# dependencies = [
#   "pytest>=7.0.0",
#   "pytest-cov>=4.0.0",
#   "boto3>=1.26.0",
#   "pyyaml>=6.0",
#   "rich>=13.0.0",
# ]
# ///
"""Run unit tests for Spot Deployer."""

import subprocess
import sys
from pathlib import Path

# Add the spot directory to Python path
sys.path.insert(0, str(Path(__file__).parent))


def main():
    """Run tests with coverage."""
    # Run pytest with coverage
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "-v",  # Verbose output
        "--cov=spot_deployer",  # Coverage for spot_deployer package
        "--cov-report=term-missing",  # Show missing lines
        "--cov-report=html",  # Generate HTML report
        "-x",  # Stop on first failure
    ]

    print("Running unit tests with coverage...\n")

    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("\n✅ All tests passed!")
        print("\nCoverage report saved to htmlcov/index.html")
    else:
        print("\n❌ Tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
