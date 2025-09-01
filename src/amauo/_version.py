"""Version management for amauo package."""

from pathlib import Path

# Get the directory where this file is located
_this_dir = Path(__file__).parent

# Read version from __version__ file
_version_file = _this_dir / "__version__"
with open(_version_file, "r") as f:
    __version__ = f.read().strip()

version = __version__

# Create version tuple
version_parts = __version__.split(".")
__version_tuple__ = tuple(int(p) for p in version_parts if p.isdigit())
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
