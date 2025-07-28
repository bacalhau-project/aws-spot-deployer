"""Version information for spot-deployer."""

import subprocess


def get_version():
    """Get version from git tags with commit hash."""
    try:
        # Try to get the current tag
        result = subprocess.run(
            ["git", "describe", "--tags", "--exact-match"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            # We're on a tag, use it (remove 'v' prefix if present)
            tag = result.stdout.strip()
            return tag.lstrip("v")

        # Not on a tag, get the most recent tag and commit hash
        tag_result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"], capture_output=True, text=True, check=False
        )

        hash_result = subprocess.run(
            ["git", "rev-parse", "--short=6", "HEAD"], capture_output=True, text=True, check=False
        )

        if tag_result.returncode == 0 and hash_result.returncode == 0:
            # Got previous tag and commit hash
            prev_tag = tag_result.stdout.strip().lstrip("v")
            commit_hash = hash_result.stdout.strip()
            return f"{prev_tag}+{commit_hash}"

        # No tags but have commit hash
        if hash_result.returncode == 0:
            commit_hash = hash_result.stdout.strip()
            return f"0.0.0+{commit_hash}"

        # No git info available
        return "1.0.0+unknown"

    except Exception:
        # Git not available or other error
        return "1.0.0+unknown"


__version__ = get_version()
