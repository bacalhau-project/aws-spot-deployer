"""Version management for amauo package."""

import os
import subprocess
from pathlib import Path

# Get the directory where this file is located
_this_dir = Path(__file__).parent

# Read version from __version__ file
_version_file = _this_dir / "__version__"
with open(_version_file, "r") as f:
    _base_version = f.read().strip()


def _get_dev_version():
    """Generate a development version with timestamp if base version is 0.0.0."""
    if _base_version == "0.0.0":
        try:
            # Get latest git tag
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                capture_output=True,
                text=True,
                cwd=_this_dir,
            )
            if result.returncode == 0:
                latest_tag = result.stdout.strip().lstrip("v")
                # Generate timestamp-based dev version
                import datetime

                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                return f"{latest_tag}.dev{timestamp}"
        except:
            pass
        # Fallback if git fails
        import datetime

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        return f"0.1.0.dev{timestamp}"
    return _base_version


# Set the version
__version__ = _get_dev_version()
version = __version__

# Create version tuple
version_parts = __version__.replace(".dev", ".0.dev").split(".")
__version_tuple__ = tuple(int(p) if p.isdigit() else p for p in version_parts)
version_tuple = __version_tuple__

# Git commit info (not used but kept for compatibility)
__commit_id__ = None
commit_id = None

# Export all expected attributes
__all__ = [
    "__version__",
    "__version_tuple__",
    "version",
    "version_tuple",
    "__commit_id__",
    "commit_id",
]
