"""
SkyPilot Spot Deployer - Global cluster deployment made simple.

Deploy Bacalhau compute clusters across multiple cloud regions with one command.
Uses SkyPilot for cloud orchestration and spot instance management.
"""

import subprocess
from pathlib import Path

__author__ = "SkyPilot Deployer Team"
__email__ = "deployer@skypilot.co"

from .manager import ClusterManager

# Static version for packaging - will be updated by CI/CD
__version__ = "2.0.0"


def get_runtime_version() -> str:
    """Get dynamic version at runtime from git tags."""
    try:
        # Try to get version from git
        repo_root = Path(__file__).parent.parent.parent

        # Check if we're in a git repository
        git_dir = repo_root / ".git"
        if not git_dir.exists():
            return __version__

        # Try to get exact tag match first
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--exact-match", "HEAD"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=True,
            )
            tag = result.stdout.strip()
            # Remove 'v' prefix if present
            return tag[1:] if tag.startswith("v") else tag
        except subprocess.CalledProcessError:
            pass

        # Get tag + commits + sha for development builds
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--always", "--dirty"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=True,
            )
            tag_sha = result.stdout.strip()
            # Remove 'v' prefix if present
            version = tag_sha[1:] if tag_sha.startswith("v") else tag_sha

            return version
        except subprocess.CalledProcessError:
            pass

        # Fallback to just SHA
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=True,
            )
            sha = result.stdout.strip()
            return f"2.0.0-dev-{sha}"
        except subprocess.CalledProcessError:
            pass

    except Exception:
        pass

    return __version__


__all__ = ["ClusterManager"]
