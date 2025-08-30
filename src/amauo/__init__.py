"""
Amauo - AWS Spot Instance Deployment Tool.

Deploy Bacalhau compute nodes across multiple AWS regions using spot instances
for cost-effective distributed computing.
"""

__author__ = "Amauo Team"
__email__ = "hello@amauo.dev"

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


__all__ = ["get_runtime_version"]
