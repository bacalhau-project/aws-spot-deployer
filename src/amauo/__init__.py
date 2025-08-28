"""
SkyPilot Spot Deployer - Global cluster deployment made simple.

Deploy Bacalhau compute clusters across multiple cloud regions with one command.
Uses SkyPilot for cloud orchestration and spot instance management.
"""

__author__ = "Amauo Team"
__email__ = "hello@amauo.dev"

from .manager import ClusterManager

# Version is now managed by hatch-vcs from git tags
try:
    from importlib.metadata import version

    __version__ = version("amauo")
except ImportError:
    # Fallback for development/editable installs
    __version__ = "dev"


def get_runtime_version() -> str:
    """Get the package version."""
    return __version__


__all__ = ["ClusterManager"]
