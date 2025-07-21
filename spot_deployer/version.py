"""Version information for spot-deployer."""

import subprocess
from datetime import datetime


def get_version():
    """Get version from git tags or generate a development version."""
    try:
        # Try to get the current tag
        result = subprocess.run(
            ["git", "describe", "--tags", "--exact-match"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            # We're on a tag, use it (remove 'v' prefix if present)
            tag = result.stdout.strip()
            return tag.lstrip('v')
        
        # Not on a tag, get the most recent tag
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            # Got previous tag, append date
            prev_tag = result.stdout.strip().lstrip('v')
            date_str = datetime.now().strftime("%Y%m%d")
            return f"{prev_tag}-{date_str}"
        
        # No tags at all, use default
        return f"0.0.0-{datetime.now().strftime('%Y%m%d')}"
        
    except Exception:
        # Git not available or other error, use default
        return "1.0.0-dev"


__version__ = get_version()